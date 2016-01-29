from django.core.management.base import BaseCommand, CommandError

from browser.models import URLBase


class Command(BaseCommand):
    help = 'Adds base urls for the images to the database.'

    def handle(self, *args, **options):

        url_bases = []

        url_obj = {
            'name': 'cvl_coco_train2014',
            'url': 'https://vision.ece.vt.edu/data/mscoco/images/train2014/'}
        url_bases.append(url_obj)

        url_obj = {
            'name': 'cvl_coco_val2014',
            'url': 'https://vision.ece.vt.edu/data/mscoco/images/val2014/'}
        url_bases.append(url_obj)

        url_obj = {
            'name': 'cvl_coco_test2015',
            'url': 'https://vision.ece.vt.edu/data/mscoco/images/test2015/'}
        url_bases.append(url_obj)

        url_obj = {
            'name': 'cvl_as2_train2015',
            'url': 'https://vision.ece.vt.edu/vqa/release_data/abstract_v002/scene_img/img_train2015/'}
        url_bases.append(url_obj)

        url_obj = {
            'name': 'cvl_as2_val2015',
            'url': 'https://vision.ece.vt.edu/vqa/release_data/abstract_v002/scene_img/img_val2015/'}
        url_bases.append(url_obj)

        url_obj = {
            'name': 'cvl_as2_test2015',
            'url': 'https://vision.ece.vt.edu/vqa/release_data/abstract_v002/scene_img/img_test2015/'}
        url_bases.append(url_obj)

        for ub in url_bases:
            if not URLBase.objects.filter(name=ub['name']).exists():
                url = URLBase(name=ub['name'], url=ub['url'])
                url.save()
