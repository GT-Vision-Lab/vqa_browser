from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Count

import logging

from .models import URLBase, \
    ImageCOCO, ImageAS, \
    CategoryCOCO, CategoryAS, \
    AnnotationCOCO, AnnotationAS, \
    AnnotationCountCOCO, AnnotationCountAS, \
    CaptionCOCO, CaptionAS, \
    QuestionCOCO, QuestionAS, \
    AnswerCOCO, AnswerAS

logger = logging.getLogger('django.request')

#@xframe_options_exempt


def index(request):

    qs_dict = request.GET
    num_cat = 0
    keys = qs_dict.keys()
    for key in keys:
        if 'ann' in key:
            num_cat += 1
    dataset = 'mscoco'

    if 'dataset' in qs_dict:
        dataset = qs_dict['dataset']
        logger.error(str(qs_dict))

    if dataset == 'mscoco':
        Image = ImageCOCO
        Category = CategoryCOCO
        Annotation = AnnotationCOCO
        AnnotationCount = AnnotationCountCOCO
        Caption = CaptionCOCO
        Question = QuestionCOCO
        Answer = AnswerCOCO
    elif dataset == 'abstract':
        Image = ImageAS
        Category = CategoryAS
        Annotation = AnnotationAS
        AnnotationCount = AnnotationCountAS
        Caption = CaptionAS
        Question = QuestionAS
        Answer = AnswerAS

    if 'cap' in qs_dict:
        cap_search = qs_dict['cap']
        logger.error(cap_search)

    if num_cat > 0:
        req_cat = [qs_dict['ann' + str(idx + 1)] for idx in range(0, num_cat)]
    else:
        req_cat = []

    len_objs = URLBase.objects.all().count()
    if len_objs == 0:
        resp = 'No data yet.'
        return HttpResponse(resp)

    resp = ''
    all_imgs = False
    cats = Category.objects.all().order_by('cat_id')

    for cat in cats:
        resp += '{0:03d}: {1},&#09;'.format(cat.cat_id, cat.cat_name)
    resp += '</br>'
    if 'cap' in qs_dict:
        if num_cat > 0:
            imgs_l = AnnotationCount.objects \
                .filter(cat_id__in=req_cat) \
                .values('image') \
                .annotate(num_cat=Count('image')) \
                .values('image', 'num_cat') \
                .filter(num_cat__gte=len(req_cat)) \
                .values_list('image', flat=True) \
                .order_by('image')
            
            imgs_c = Caption.objects \
                .filter(image__in=imgs_l, caption__icontains=cap_search) \
                .order_by('image') \
                .distinct('image') \
                .values('image')
            imgs = imgs_c
        else:
            imgs = Caption.objects \
                .filter(caption__icontains=cap_search) \
                .order_by('image') \
                .distinct('image') \
                .values('image')
# istartswith
# iendswith
# icontains
# iregex
    else:
        if num_cat > 0:
            imgs = AnnotationCount.objects \
                .filter(cat_id__in=req_cat) \
                .values('image') \
                .annotate(num_cat=Count('image')) \
                .values('image', 'num_cat') \
                .filter(num_cat__gte=len(req_cat)) \
                .order_by('image')
        else:
            imgs = Image.objects.all().order_by('image_id')
            all_imgs = True

    resp += '</br>Total search results: ' + str(len(imgs)) + '</br>'
    for imgi in imgs[:20]:
        if all_imgs:
            img = imgi
        else:
            img = Image.objects.get(image_id=imgi['image'])
        resp += str(img.image_name)  + '</br>' 
        img_str_fmt = '<img src="{}">'
        img_str = img_str_fmt.format(img.get_url())
        resp += img_str + '</br>'
        caps = Caption.objects.filter(image=img)
        for cap in caps:
            resp += str(cap.caption) + '</br>'
        resp += '</br>'
        quess = Question.objects.filter(image=img)
        for ques in quess:
            resp += '<b>' + str(ques.question) + '</b></br>'
            resp += 'Answers: '
            anss = Answer.objects.filter(ques=ques, is_ans_img=True)
            for ans in anss:
                resp += str(ans.answer) + ', '
            resp += '</br></br>'
            resp += 'Commonsense answers: '
            anss = Answer.objects.filter(ques=ques, is_ans_no_img=True)
            for ans in anss:
                resp += str(ans.answer) + ', '
            resp += '</br></br>'
            anss = Answer.objects.filter(ques=ques, is_ans_mc_img=True)
            resp += 'Multiple-choice options: '
            for ans in anss:
                resp += str(ans.answer) + ', '
            resp += '</br></br>'
    return HttpResponse(resp)
