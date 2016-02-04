import logging
import json
import random
from math import ceil

from django.http import HttpResponse, HttpResponseRedirect
#from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.db.models import Q

from .models import URLBase, \
    ImageCOCO, ImageAS, \
    CategoryCOCO, CategoryAS, \
    AnnotationCOCO, AnnotationAS, \
    AnnotationCountCOCO, AnnotationCountAS, \
    CaptionCOCO, CaptionAS, \
    QuestionCOCO, QuestionAS, \
    AnswerCOCO, AnswerAS

logger = logging.getLogger('django.request')

def generic_request_handler(request, data_get_process, data_post_process):
    
    resp = 'Default response.'
    print('\nRequest Handler\n')
    print((request.method, request.GET))
    if request.method == 'GET':

        print("\n  DJANGO_GET\n")
        response = data_get_process(request.GET)  

    elif request.method == 'POST':

        print("\n  DJANGO_POST\n")

        post_data = json.loads(request.POST['resp'])
        print(post_data)
        print('')

        resp = data_post_process(post_data)
#       print(resp)

        response = HttpResponse(json.dumps(resp), 
                                content_type="application/json")

    response["Access-Control-Allow-Origin"] = "*"  
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"  
    response["Access-Control-Max-Age"] = "1000"  
    response["Access-Control-Allow-Headers"] = "*"  
    
    return response

def categories_get_function(get_data):

    dataset = 'mscoco'

    if 'dataset' in get_data:
        dataset = get_data['dataset']
 
    if dataset == 'mscoco':
        Category = CategoryCOCO
    elif dataset == 'abstract':
        Category = CategoryAS
    
    cat_objs = Category.objects.all().order_by('cat_id')

    cats = []
    for cat_obj in cat_objs:
        obj = {'id': cat_obj.cat_id,
               'name': cat_obj.cat_name,
               'supercategory': cat_obj.cat_sc,
        }
        cats.append(obj)
   
    response = HttpResponse(json.dumps(cats),
                            content_type="application/json") 
    return response

@csrf_exempt
def categories(request):
    return generic_request_handler(request,
                                   categories_get_function,
                                   None)
@csrf_exempt
def index(request):
    return generic_request_handler(request,
                                   index_get_function,
                                   None)

def index_get_function(get_data):

    if 'req' in get_data:
        req = index_get_ajax(get_data['req'])
        resp = json.dumps(req)
        response = HttpResponse(resp, 
                                content_type="application/json")
    else:
        resp = index_simple(get_data)
        response = HttpResponse(resp)

    return response

def index_get_ajax(get_data):
    
    logger.error(get_data)
    param = json.loads(get_data)
    dataset = param['dataset']

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

    rand_seed = param['randSeed']
    max_imgs_page = param['maxImgsPerPage']
    cur_page = param['curPage']
    show_all_data = param['showAllDataEachImg']
    req_cat = param['categoryFilter']
    search_methods = param['searchMethods']
    search_strs = param['searchStrs']
    ans_types = ans_type_list(param['quesSearchKeep'])
    ans_search_keep = param['ansSearchKeep']
    cur_page_data = []

    resp = {
        'curPageData': [],
        'numPages': 0,
        'numSearchImgs': 0,
        'numSearchQs': 0,
        'numSearchAs': 0,
        'numSearchCaps': 0,
        'numTotalImgs': 0,
        'numTotalQs': 0,
        'numTotalAs': 0,
        'numTotalCaps': 0,
    }
 
    if len(ans_types) > 0:
#        req_cat = [1, 82, 90]
        iid = object_search(AnnotationCount, req_cat)

        if iid is None or len(iid) > 0:
            logger.error('question')

            iqid = question_search(Question,
                                   search_methods['ques'],
                                   search_strs['ques'],
                                   ans_types,
                                   iid)

            if iqid is None or len(iqid) > 0:

                logger.error('answer')
                iqaid = answer_search(Answer,
                                      search_methods['ans'],
                                      search_strs['ans'],
                                      ans_search_keep,
                                      iqid)

                if iqaid is None or len(iqaid) > 0:
                    logger.error('caption')
                    icid = caption_search(Caption,
                                          search_methods['cap'],
                                          search_strs['cap'],
                                          iqaid)
                   
                    if icid is None: 

                        data = Image.objects.all() \
                               .order_by('image_id') \
                               .values_list('image_id', flat=True)

                        if rand_seed >= 0:
                            indices = range(0, len(data))
                            random.seed(rand_seed)
                            random.shuffle(indices)
                        else:
                            indices = None

                        imgs,num_pages = get_current_page_subset(cur_page,
                                                                 max_imgs_page,
                                                                 data,
                                                                 indices=indices)
                        logger.error(len(imgs))
                    elif len(icid) > 0:
                        # Update iid/iqid/iqaid 
                        # to make sure they're consistent
                        # with later searches
                        if not show_all_data:
                            final_imgs = {d['image'] for d in icid}
                            final_iqid = []
                            final_iqaid = []

                            for d in iqid:
                                if d['image'] in final_imgs:
                                    final_iqid.append(d)
                            for d in iqaid:
                                if d['image'] in final_imgs:
                                    final_iqaid.append(d)
                            logger.error(len(icid))
                            logger.error(len(iqaid))
                            logger.error(len(final_iqaid))
                            
                            img2idx = {}
                            all_imgs = [d['image'] for d in icid]
                            if rand_seed >= 0:
                                indices = range(0, len(all_imgs))
                                random.seed(rand_seed)
                                random.shuffle(indices)
                            else:
                                indices = None

                            imgs, num_pages = get_current_page_subset(cur_page,
                                                                            max_imgs_page,
                                                                            all_imgs,
                                                                            indices=indices)

                    final_imgs = Image.objects.filter(image_id__in=imgs).order_by('image_id')

                    logger.error(final_imgs[0])
                    data = []
                    
                    for idx, d in enumerate(final_imgs):
                        img_obj = { 'img': d.image_name,
                                    'imgID': d.image_id,
                                    'url': d.get_url(),
                                    'uniqueIndex': idx+1,
                                    'questions': [],
                                    'captions': [],
                                  }
                        questions = []
                        qs = Question.objects.filter(image=d).order_by('ques_id')
                        for q in qs:
                            a = Answer.objects.get(ques_id=q.ques_id, is_ans_mc_img=True)
                            mc_ans = json.loads(a.answer)
                            a = Answer.objects.filter(ques_id=q.ques_id, is_ans_no_img=True)
                            no_img = [{'ansNum': d.ans_num, 'ansStr': d.answer} for d in a]
                            a = Answer.objects.filter(ques_id=q.ques_id, is_ans_img=True)
                            img = [{'ansNum': d.ans_num, 'ansStr': d.answer} for d in a]
                            
                            q_obj = { 'quesStr': q.question,
                                     'quesID': q.ques_id,
                                      'quesType': q.ques_type,
                                      'ansType': q.ans_type,
                                      'ansMCImg': mc_ans,
                                      'ansImg': img,
                                      'ansNoImg': no_img,
                                    }
                            questions.append(q_obj)
                        img_obj['questions'] = questions
                        
                        caps = Caption.objects.filter(image=d).order_by('cap_id').values('caption', 'cap_id')
                        caps = [{'caption': c['caption'], 'cap_id':c['cap_id']} for c in caps]
                        img_obj['captions'] = caps
                        data.append(img_obj)

                    cur_page_data = data

                    logger.error(len(cur_page_data))

                    resp['curPageData'] = cur_page_data
                    resp['numPages'] = num_pages
                    resp['numSearchImgs'] = 1#len(cur_page_data)
                    resp['numSearchQs'] = 1#len(final_iqid) 
                    resp['numSearchAs'] = 1#len(final_iqaid)
                    resp['numSearchCaps'] = 1#len(icid)
                    resp['numTotalImgs'] = Image.objects.all().count()
                    resp['numTotalQs'] = Question.objects.all().count()
                    Qr = Q(is_ans_img=True) | Q(is_ans_no_img=True)
                    resp['numTotalAs'] = Answer.objects.filter(Qr).count()
                    resp['numTotalCaps'] = Caption.objects.all().count()
 
    return resp

ans_type_mapping = {'binary': 'yes/no',
                    'number': 'number',
                    'other': 'other',
                    }

ans_search_mapping = {'gt': 'is_ans_img',
                      'cs': 'is_an_no_img',
                    }

def get_current_page_subset(cur_page, max_per_page, data, indices=None):

    num_total_pages = int(ceil(len(data)/float(max_per_page)))

    if cur_page < 0:
        cur_page = 0 
    elif cur_page >= num_total_pages:
        cur_page = num_total_pages - 1 

    if indices == None:
        subset = data[cur_page*max_per_page:(cur_page+1)*max_per_page]
    else:
        subset = map(data.__getitem__, 
                        indices[cur_page*max_per_page:(cur_page+1)*max_per_page])

    return subset, num_total_pages

def caption_search(Caption,
                                      search_method,
                                      search_str,
                                      iqaid):
# Assumes iqid is None or > 0 elements

    str_search = len(search_str.strip()) != 0

    if str_search:
        kwargs = {'caption__{}'.format(search_method): search_str}
        Qr = Q(**kwargs)
        
        if iqaid is not None:
            imgs = [d['image'] for d in iqaid]
            q = Q(image__in=imgs)
            Qr = Qr & q
                
        icid = Caption.objects.filter(Qr) \
                .values('image', 'cap_id')
    else:
        icid = iqaid

    if icid is not None and len(icid) > 0:
        logger.error(icid[:5])

    return icid

def answer_search(Answer,
                                      search_method,
                                      search_str,
                                      ans_search_keep,
                                      iqid):
# Assumes iqid is None or > 0 elements

    str_search = len(search_str.strip()) != 0


    if str_search:

        Qr_sk = None
        for key, val in ans_search_keep.items():
            if val:
                kwargs = {'{}'.format(ans_search_mapping[key]): True}
                q = Q(**kwargs)
                if Qr_sk:
                    # Change the '|' to '&' if want
                    # search string to be in both
                    Qr_sk = Qr_sk | q
                else:
                    Qr_sk = q

        if Qr_sk:
            kwargs = {'answer__{}'.format(search_method): search_str}
            Qr = Q(**kwargs)
            Qr = Qr & Qr_sk
            
            if iqid is not None:
                d = iqid[0]
                if 'ques_id' in d:
                    ques_ids = [d['ques_id'] for d in iqid]
                    q = Q(ques_id__in=ques_ids)
                    Qr = Qr & q
                else:
                    imgs = iqid
                    #imgs = [d['image'] for d in iqid]
                    q = Q(image__in=imgs)
                    Qr = Qr & q
                    
            iqaid = Answer.objects.filter(Qr) \
                    .values('image', 'ques_id', 'ans_num')
        else:
           iqaid = [] 
            
    else:
        iqaid = iqid

    if iqaid is not None and len(iqaid) > 0:
        logger.error(iqaid[:5])

    return iqaid

def question_search(Question,
                                   search_method,
                                   search_str,
                                   ans_types,
                                   iid):
# Assumes ans_types is never empty list
    
    str_search = len(search_str.strip()) != 0
    all_types = len(ans_types) == len(ans_type_mapping)

    all_questions = not str_search and all_types

    if not all_questions:
        Qr = None

        if iid is not None:
            q = Q(image__in=iid)
            if Qr:
                Qr = Qr & q
            else:
                Qr = q

        if not all_types:
            q = Q(ans_type__in=ans_types)
            if Qr:
                Qr = Qr & q
            else:
                Qr = q

        if str_search:
            kwargs = {'question__{}'.format(search_method): search_str}
            q = Q(**kwargs)
            if Qr:
                Qr = Qr & q
            else:
                Qr = q

        iqid = Question.objects \
                .filter(Qr) \
                .values('image', 'ques_id')
    else:
        iqid = iid

    if iqid is not None and len(iqid) > 0:
        logger.error(iqid[:5])

    return iqid

def ans_type_list(ques_search_keep):

    ans_types = [ans_type_mapping[t] 
                for t in ques_search_keep 
                    if ques_search_keep[t]]

    return ans_types

def idx(get_data):
    pass

def object_search(AnnotationCount, req_cat):

    if len(req_cat) == 0:
        iid = None
    else:
        iid = AnnotationCount.objects \
              .filter(cat_id__in=req_cat) \
              .values('image') \
              .annotate(num_cat=Count('image')) \
              .values('image', 'num_cat') \
              .filter(num_cat__gte=len(req_cat)) \
              .values('image')

    return iid

def index_simple(get_data):

    qs_dict = get_data
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
            logger.error(type(imgs_l)) 
            imgs_c = Caption.objects \
                .filter(image__in=imgs_l, caption__icontains=cap_search) \
                .order_by('image') \
                .distinct('image') \
                .values('image')
            logger.error(type(imgs_c))
            if 'ques' in qs_dict:
                imgs_d = Question.objects \
                        .filter(image__in=imgs_c,
                                question__icontains=qs_dict['ques']) \
                        .values('image') \
                        .order_by('image')
                logger.error(imgs_d)
                imgs = imgs_d

                
                logger.error(imgs)
            else:
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

            d = AnnotationCount.objects \
                .filter(cat_id__in=req_cat) \
                .values('image') \
                .annotate(num_cat=Count('image')) \
                .values('image', 'num_cat') \
                .filter(num_cat__gte=len(req_cat)) \
                .order_by('image_id')

               # .filter(num_cat__gte=len(req_cat)) \
            img_ls = ''
            for b in d:
                img_ls += str(b['image']) + '-' + str(b['num_cat']) + ', '
                #pass
            logger.error(img_ls)
            logger.error(len(d))
            logger.error(len(req_cat))
            logger.error(b.keys())
            logger.error(str(b['image']) + '-'+ str(b['num_cat']))
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
    return resp
