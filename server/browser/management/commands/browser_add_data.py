from os import getcwd
from os import path
import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db import transaction

from browser.models import URLBase, \
    ImageCOCO, ImageAS, \
    CategoryCOCO, CategoryAS, \
    AnnotationCOCO, AnnotationAS, \
    AnnotationCountCOCO, AnnotationCountAS, \
    CaptionCOCO, CaptionAS, \
    QuestionCOCO, QuestionAS, \
    AnswerCOCO, AnswerAS

# If true, doesn't bother checking if exists
FORCE = True

ann_data_dir = '/opt/browser_data'


class Command(BaseCommand):
    help = 'Adds all the browser data for the images.'

    def handle(self, *args, **options):

        commands = [
            'images',
            'annotations',
            'annotationcounts',
            'captions',
            'vqas',
        ]

        datasets = ['abstract_v002', 'mscoco']
#        datasets = ['abstract_v002']
#        datasets = ['mscoco']

        subsets = {
            'abstract_v002': ['val2015', 'train2015'],
            'mscoco': ['val2014', 'train2014'],
        }

#        subsets = {
#                    'abstract_v002': ['val2015'],
#                    'mscoco': ['val2014'],
#                  }

        for dataset in datasets:
            for subset in subsets[dataset]:
                for command in commands:
                    self.run_command(dataset, subset, command)

    def run_command(self, dataset, subset, command):

        if dataset == 'mscoco':
            base_url = URLBase.objects.get(name='cvl_coco_{}'.format(subset))
            Image = ImageCOCO
            Category = CategoryCOCO
            Annotation = AnnotationCOCO
            AnnotationCount = AnnotationCountCOCO
            Caption = CaptionCOCO
            Question = QuestionCOCO
            Answer = AnswerCOCO
        elif dataset == 'abstract_v002':
            base_url = URLBase.objects.get(name='cvl_as2_{}'.format(subset))
            Image = ImageAS
            Category = CategoryAS
            Annotation = AnnotationAS
            AnnotationCount = AnnotationCountAS
            Caption = CaptionAS
            Question = QuestionAS
            Answer = AnswerAS

        if command == 'images':
            afn_fmt = '{}_instances_{}.json'
            afn = afn_fmt.format(dataset, subset)
            fn = path.join(ann_data_dir, afn)
            with open(fn, 'r') as ifp:
                all_data = json.load(ifp)
            print('Adding images to db {}_{}...'.format(dataset, subset))
            self.add_images(all_data, dataset, subset, Image, base_url)
        elif command == 'annotations':
            afn_fmt = '{}_instances_{}.json'
            afn = afn_fmt.format(dataset, subset)
            fn = path.join(ann_data_dir, afn)
            with open(fn, 'r') as ifp:
                all_data = json.load(ifp)
            print('Adding instance annotations to db {}_{}...'.format(dataset, subset))
            self.add_obj_annotations(
                all_data, dataset, subset, Image, Category, Annotation)
        elif command == 'annotationcounts':
            print('Adding annotation sums/counts to db {}_{}...'.format(dataset, subset))
            self.calc_obj_ann_counts(
                dataset, subset, Image, Annotation, AnnotationCount)
        elif command == 'captions':
            afn_fmt = '{}_captions_{}.json'
            afn = afn_fmt.format(dataset, subset)
            fn = path.join(ann_data_dir, afn)
            with open(fn, 'r') as ifp:
                all_data = json.load(ifp)
            print('Adding captions to db {}_{}...'.format(dataset, subset))
            self.add_captions(all_data, dataset, subset, Image, Caption)
        elif command == 'vqas':
            afn_fmt = '{}_vqas_{}.json'
            afn = afn_fmt.format(dataset, subset)
            fn = path.join(ann_data_dir, afn)
            with open(fn, 'r') as ifp:
                all_data = json.load(ifp)
            print('Adding vqa data to db {}_{}...'.format(dataset, subset))
            self.add_vqas(all_data, dataset, subset, Image, Question, Answer)

#    @transaction.atomic
    def add_images(self, all_data, dataset, subset,
                   Image, url_base):

        for data in all_data['images']:
            img = {
                'image_id': data['id'],
                'image_name': data['file_name'],
                'subset': subset,
                'url_base': url_base,
            }

            if FORCE or not Image.objects.filter(
                    image_id=img['image_id']).exists():
                img_obj = Image(image_name=img['image_name'],
                                image_id=img['image_id'],
                                subset=img['subset'],
                                url_base=img['url_base']
                                )
                img_obj.save()

#    @transaction.atomic
    def add_obj_annotations(self, all_data, dataset, subset,
                            Image, Category, Annotation):

        for data in all_data['categories']:
            cat_obj = Category(cat_sc=data['supercategory'],
                               cat_id=data['id'],
                               cat_name=data['name'])
            cat_obj.save()

        if dataset == 'mscoco':
            for data in all_data['annotations']:
                if FORCE or not Annotation.objects.filter(
                        ann_id=data['id']).exists():
                    img_obj = Image.objects.get(image_id=data['image_id'])
                    ann_obj = Annotation(image=img_obj,
                                         ann_id=data['id'],
                                         cat_id=data['category_id'],
                                         iscrowd=data['iscrowd'],
                                         bbox=data['bbox'],
                                         segmentation=data['segmentation']
                                         )
                    ann_obj.save()
        elif dataset == 'abstract_v002':
            for data in all_data['annotations']:
                if FORCE or not Annotation.objects.filter(
                        ann_id=data['id']).exists():
                    img_obj = Image.objects.get(image_id=data['image_id'])
                    ann_obj = Annotation(image=img_obj,
                                         ann_id=data['id'],
                                         cat_id=data['category_id'],
                                         position=data['position']
                                         )
                    ann_obj.save()

#    @transaction.atomic
    def calc_obj_ann_counts(self, dataset, subset,
                            Image, Annotation, AnnotationCount):

        data = Annotation.objects.values('image', 'cat_id') \
            .annotate(inst_count=Count('image')) \
            .values('image', 'cat_id', 'inst_count')

        for datum in data:
            if FORCE or not AnnotationCount.objects \
                    .filter(image=datum['image'], cat_id=datum['cat_id']) \
                    .exists():
                img_obj = Image.objects.get(image_id=datum['image'])
                ann_count = AnnotationCount(image=img_obj,
                                            cat_id=datum['cat_id'],
                                            cat_count=datum['inst_count']
                                            )
                ann_count.save()

#    @transaction.atomic
    def add_captions(self, all_data, dataset, subset,
                     Image, Caption):

        for data in all_data['annotations']:
            if FORCE or not Caption.objects.filter(cap_id=data['id']).exists():
                img_obj = Image.objects.get(image_id=data['image_id'])

                ann_obj = Caption(image=img_obj,
                                  cap_id=data['id'],
                                  caption=data['caption'],
                                  )
                ann_obj.save()

#    @transaction.atomic
    def add_vqas(self, all_data, dataset, subset,
                 Image, Question, Answer):

        for img in all_data:
            img_data = all_data[img]
            img_parts = img.split('_')
            img_id = int(img_parts[-1].split('.')[0])

            img_obj = Image.objects.get(image_id=img_id)

            for img_key in img_data:
                if img_key in [str(idx) for idx in range(1, 11)]:
                    ques_data = img_data[img_key]
                    if FORCE or not Question.objects.filter(
                            ques_id=data['quesID']).exists():
                        q = Question(
                            image=img_obj,
                            ques_id=ques_data['quesID'],
                            question=ques_data['quesStr'].encode('utf-8'),
                            ques_type=ques_data['quesType'],
                            ans_type=ques_data['ansType'])
                        q.save()

                        for ques_key in ques_data:
                            if ques_key == 'ansImg':
                                for ans in ques_data[ques_key]:
                                    a = Answer(
                                        image=img_obj,
                                        ques=q,
                                        answer=ans['ansStr'].encode('utf-8'),
                                        ans_num=ans['ansNum'],
                                        is_ans_img=True,
                                        is_ans_no_img=False,
                                        is_ans_mc_img=False)
                                    a.save()
                            elif ques_key == 'ansNoImg':
                                for ans in ques_data[ques_key]:
                                    a = Answer(
                                        image=img_obj,
                                        ques=q,
                                        answer=ans['ansStr'].encode('utf-8'),
                                        ans_num=ans['ansNum'],
                                        is_ans_img=False,
                                        is_ans_no_img=True,
                                        is_ans_mc_img=False)
                                    a.save()
                            elif ques_key == 'ansMCImg':
                                answ = [ans for ans in ques_data[ques_key]]
                                ans = json.dumps(answ)
                                a = Answer(image=img_obj,
                                           ques=q,
                                           answer=ans,
                                           ans_num=1,
                                           is_ans_img=False,
                                           is_ans_no_img=False,
                                           is_ans_mc_img=True)
                                a.save()
