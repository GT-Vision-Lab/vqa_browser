from django.db import models
from django.contrib.postgres.fields import JSONField

# Due to Django not supporting multiple-column primary keys
# and wanting to use the image ids as the primary key,
# we'll have two sets of tables, one for MSCOCO and one
# for abstract scenes.


class URLBase(models.Model):

    name = models.CharField(db_index=True, max_length=20)

    url = models.URLField(max_length=200)

    def __str__(self):
        return self.url


class Image(models.Model):

    image_id = models.BigIntegerField(db_index=True, primary_key=True)

    image_name = models.CharField(db_index=True, max_length=50)

    subset = models.CharField(db_index=True, max_length=20)

    url_base = models.ForeignKey('URLBase')

    class Meta:
        abstract = True

    def get_url(self):
        return str(self.url_base) + self.image_name

    def __str__(self):
        return str(self.image_name)


class ImageCOCO(Image):
    pass


class ImageAS(Image):
    pass


class Category(models.Model):

    cat_id = models.PositiveIntegerField(db_index=True)

    cat_name = models.CharField(db_index=True, max_length=50)

    # Supercategory
    cat_sc = models.CharField(db_index=True, max_length=50)

    class Meta:
        abstract = True

    def __str__(self):
        return '{0}, {1:03d}, {2}'.format(self.cat_sc,
                                          self.cat_id,
                                          self.cat_name)


class CategoryCOCO(Category):
    pass


class CategoryAS(Category):
    pass


class AnnotationCOCO(models.Model):

    image = models.ForeignKey('ImageCOCO', db_index=True)

    ann_id = models.BigIntegerField(db_index=True)

    cat_id = models.PositiveIntegerField(db_index=True)

    iscrowd = models.BooleanField(db_index=True, default=False)

    bbox = JSONField()

    segmentation = JSONField()

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.ann_id, self.cat_id)


class AnnotationCountCOCO(models.Model):

    image = models.ForeignKey('ImageCOCO', db_index=True)

    cat_id = models.PositiveIntegerField(db_index=True)

    cat_count = models.PositiveIntegerField(db_index=True)

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.cat_id, self.cat_count)


class AnnotationAS(models.Model):

    image = models.ForeignKey('ImageAS', db_index=True)

    ann_id = models.BigIntegerField(db_index=True)

    cat_id = models.PositiveIntegerField(db_index=True)

    position = JSONField()

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.ann_id, self.cat_id)


class AnnotationCountAS(models.Model):

    image = models.ForeignKey('ImageAS', db_index=True)

    cat_id = models.PositiveIntegerField(db_index=True)

    cat_count = models.PositiveIntegerField(db_index=True)

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.cat_id, self.cat_count)


class Caption(models.Model):

    cap_id = models.BigIntegerField(db_index=True)

    caption = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return '({}, {}, {})'.format(self.cap_id, self.caption)


class CaptionCOCO(Caption):

    image = models.ForeignKey('ImageCOCO', db_index=True)

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.cap_id, self.caption)


class CaptionAS(Caption):

    image = models.ForeignKey('ImageAS', db_index=True)

    def __str__(self):
        return '({}, {}, {})'.format(self.image, self.cap_id, self.caption)


class Question(models.Model):

    ques_id = models.BigIntegerField(db_index=True, primary_key=True)

    question = models.TextField()

    ques_type = models.CharField(db_index=True, max_length=60)

    ans_type = models.CharField(db_index=True, max_length=20)

    class Meta:
        abstract = True


class QuestionCOCO(Question):

    image = models.ForeignKey('ImageCOCO', db_index=True)

    def __str__(self):
        return '{}, {}, {}, {}, {}'.format(self.image, self.ques_id,
                                           self.ques_type, self.ans_type,
                                           self.question)


class QuestionAS(Question):

    image = models.ForeignKey('ImageAS', db_index=True)

    def __str__(self):
        return '{}, {}, {}, {}, {}'.format(self.image, self.ques_id,
                                           self.ques_type, self.ans_type,
                                           self.question)


class Answer(models.Model):

    answer = models.TextField()

    ans_num = models.PositiveIntegerField(db_index=True)

    is_ans_img = models.BooleanField(db_index=True, default=False)

    is_ans_no_img = models.BooleanField(db_index=True, default=False)

    is_ans_mc_img = models.BooleanField(db_index=True, default=False)

    class Meta:
        abstract = True


class AnswerCOCO(Answer):

    image = models.ForeignKey('ImageCOCO', db_index=True)

    ques = models.ForeignKey('QuestionCOCO', db_index=True)

    def __str__(self):
        return '{}, {}, {}, {}, {}, {}, {}'.format(
            self.image,
            self.ques.ques_id,
            self.ans_num,
            self.is_ans_img,
            self.is_ans_no_img,
            self.is_ans_mc_img,
            self.answer)


class AnswerAS(Answer):

    image = models.ForeignKey('ImageAS', db_index=True)

    ques = models.ForeignKey('QuestionAS', db_index=True)

    def __str__(self):
        return '{}, {}, {}, {}, {}, {}, {}'.format(
            self.image,
            self.ques.ques_id,
            self.ans_num,
            self.is_ans_img,
            self.is_ans_no_img,
            self.is_ans_mc_img,
            self.answer)
