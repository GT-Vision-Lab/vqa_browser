import logging
import json
import random
from math import ceil
import time

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
        req_d = json.loads(get_data['req'])
    else:
        req_d = {}
        req_d['dataset'] = 'mscoco'
        req_d['randSeed'] = -1
        req_d['maxImgsPerPage'] = 20
        req_d['curPage'] = 0
        req_d['showAllDataEachImg'] = False
        req_d['categoryFilter'] = [1, 82, 90]
        req_d['searchMethods'] = {'ques': 'icontains', 
                                  'ans': 'icontains', 
                                  'cap': 'icontains'}
        req_d['searchStrs'] = {'ques': '', 
                               'ans': '', 
                               'cap': ''}
        req_d['quesSearchKeep'] = {'binary': True, 
                                   'number':True, 
                                   'other': True}
        req_d['ansSearchKeep'] = {'gt': True, 
                                  'cs': False}
        

    req = index_get_ajax(req_d)
    resp = json.dumps(req)
    response = HttpResponse(resp, 
                            content_type="application/json")
    
    return response


ans_type_mapping = {'binary': 'yes/no',
                    'number': 'number',
                    'other': 'other',
                    }

ans_search_mapping = {'gt': 'is_ans_img',
                      'cs': 'is_ans_no_img',
                    }

def ans_type_list(ques_search_keep):

    ans_types = [ans_type_mapping[t] 
                for t in ques_search_keep 
                    if ques_search_keep[t]]

    return ans_types


def get_current_page_subset(cur_page, max_per_page, 
                            data, num_data, 
                            indices=None):

    num_total_pages = int(ceil(num_data/float(max_per_page)))

    if cur_page < 0:
        cur_page = 0 
    elif cur_page >= num_total_pages:
        cur_page = num_total_pages - 1 

    if indices == None:
        subset = data[cur_page*max_per_page:(cur_page+1)*max_per_page]
        page_indices = list(range(cur_page*max_per_page, 
                                  (cur_page+1)*max_per_page))
    else:
        page_indices = \
            indices[cur_page*max_per_page:(cur_page+1)*max_per_page]
        subset = map(data.__getitem__, 
                     page_indices)

    return subset, page_indices, num_total_pages

def index_get_ajax(param):

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
        'curPageData': cur_page_data,
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

    start = time.perf_counter()

    if len(ans_types) > 0:

        # Check cached search results here?

        iid, num_iid = object_search(Image,
                                     AnnotationCount,
                                     req_cat)
        total = time.perf_counter() - start
        logger.error('Object Time: {} s'.format(total))
        logger.error('{}'.format(num_iid))

        if iid is None or num_iid > 0:                
            icid, num_iid, num_icid = caption_search(Caption,
                                            search_methods['cap'],
                                            search_strs['cap'],
                                            iid,
                                            num_iid)
            total = time.perf_counter() - start
            logger.error('Caption Time: {} s'.format(total))
            logger.error('{} - {}'.format(num_iid, num_icid))

            if icid is None or num_iid > 0:
                
                iid, num_iid_new, num_iqid, num_iqaid = qa_search(Image,
                                                                Question, 
                                                                Answer, 
                                                                search_methods, 
                                                                search_strs, 
                                                                ans_types, 
                                                                ans_search_keep, 
                                                                icid, 
                                                                num_iid)

                total = time.perf_counter() - start
                logger.error('QA Time: {} s'.format(total))
                logger.error('{} - {} - {}'.format(num_iid_new, num_iqid, num_iqaid))
                if num_iid != num_iid_new:
                    iid, num_iid, num_icid = caption_search(Caption,
                                                    search_methods['cap'],
                                                    search_strs['cap'],
                                                    iid,
                                                    num_iid_new)
                    total = time.perf_counter() - start
                    logger.error('Caption Time: {} s'.format(total))
                    logger.error('{} - {}'.format(num_iid, num_icid))
                    
                if iid is None:
                    num_all_imgs = Image.objects.all().count()
                    all_imgs = Image.objects.all() \
                        .order_by('image_id') \
                        .values_list('image_id', flat=True)
                elif num_iid > 0:
                    num_all_imgs = num_iid
                    all_imgs = Image.objects \
                                .filter(image_id__in=iid) \
                                .order_by('image_id') \
                                .values_list('image_id', flat=True)
                else:
                    num_all_imgs = num_iid
                    all_imgs = []

                # Cache search results here?

                if rand_seed >= 0:
                    indices = list(range(0, num_all_imgs))
                    random.seed(rand_seed)
                    random.shuffle(indices)
                else:
                    indices = None

                imgs, idxs, num_pages = \
                    get_current_page_subset(cur_page,
                                            max_imgs_page,
                                            all_imgs,
                                            num_all_imgs,
                                            indices=indices)

                final_imgs = Image.objects.filter(image_id__in=imgs)
                total = time.perf_counter() - start
                logger.error('Image Time: {} s'.format(total))
                logger.error(len(final_imgs))


                if not show_all_data:
                    data = []
                    
                    for idx, d in enumerate(final_imgs):
                        img_obj = { 'img': d.image_name,
                                    'imgID': d.image_id,
                                    'url': d.get_url(),
                                    'uniqueIndex': idxs[idx]+1,
                                    'questions': [],
                                    'captions': [],
                                    }
                        
                        caps = Caption.objects.filter(image=d).order_by('cap_id').values('caption', 'cap_id')
                        img_obj['captions'] = [{'caption': c['caption'], 'cap_id':c['cap_id']} for c in caps]
                        
                        questions = []
                        anss = Answer.objects.filter(image=d).order_by('ques_id', 'ans_num')
                        ques_id_old = -1
                        for ans in anss:
                            ques_id = ans.ques_id
                            if ques_id != ques_id_old:
                                ques_id_old = ques_id
                                q = Question.objects.get(ques_id=ques_id)
                                q_obj = { 'quesStr': q.question,
                                        'quesID': q.ques_id,
                                        'quesType': q.ques_type,
                                        'ansType': q.ans_type,
                                        'ansMCImg': [],
                                        'ansImg': [],
                                        'ansNoImg': [],
                                    }
                                questions.append(q_obj)
                            if ans.is_ans_img:
                                q_obj['ansImg'].append({'ansNum': ans.ans_num, 'ansStr': ans.answer})
                            elif ans.is_ans_no_img:
                                q_obj['ansNoImg'].append({'ansNum': ans.ans_num, 'ansStr': ans.answer})
                            if ans.is_ans_mc_img == True:
                                q_obj['ansMCImg'] = json.loads(ans.answer)
                            
                        img_obj['questions'] = questions
                        data.append(img_obj)

                total = time.perf_counter() - start
                logger.error('Build Data Time: {} s'.format(total))
                cur_page_data = data

                logger.error(len(cur_page_data))

                resp['curPageData'] = cur_page_data
                resp['numPages'] = num_pages
                resp['numSearchImgs'] = num_all_imgs
                resp['numSearchQs'] = num_iqid
                resp['numSearchAs'] = num_iqaid
                resp['numSearchCaps'] = num_icid

                total = time.perf_counter() - start
                logger.error('Add Response Fields Time: {} s'.format(total))
    
    # Cache/load these
    resp['numTotalImgs'] = Image.objects.all().count()
    resp['numTotalQs'] = Question.objects.all().count()
    Qr = Qr_a_s_k = get_ans_gt_qsearch(ans_search_keep)
    resp['numTotalAs'] = Answer.objects.filter(Qr).count()
    resp['numTotalCaps'] = Caption.objects.all().count()
    
    total = time.perf_counter() - start
    logger.error('Response Time: {} s'.format(total))

    return resp

def object_search(Image,
                  AnnotationCount, 
                  req_cat):

    if len(req_cat) == 0:
        iid = None
        num_iid = Image.objects.all().count()
    else:
        iid = AnnotationCount.objects \
              .filter(cat_id__in=req_cat) \
              .values('image') \
              .annotate(num_cat=Count('image')) \
              .values('image', 'num_cat') \
              .filter(num_cat__gte=len(req_cat)) \
              .values('image')
        num_iid = AnnotationCount.objects \
                  .filter(cat_id__in=req_cat) \
                  .values('image') \
                  .annotate(num_cat=Count('image')) \
                  .values('image', 'num_cat') \
                  .filter(num_cat__gte=len(req_cat)) \
                  .count()

    return iid, num_iid

def caption_search(Caption,
                   search_method,
                   search_str,
                   sid,
                   num_sid):
# Assumes sid is None or > 0 elements

    if sid is not None:
        Qr = Q(image__in=sid)
    else:
        Qr = None
    
    str_search = len(search_str.strip()) != 0

    if str_search:
        kwargs = {'caption__{}'.format(search_method): search_str}
        q = Q(**kwargs)
        if Qr is not None:
            Qr = Qr & q
        else:
            Qr = q

        icid = Caption.objects.filter(Qr) \
               .values('image') \
               .distinct()
        num_iid = Caption.objects.filter(Qr) \
                .values('image') \
                .distinct() \
                .count()
        num_icid = Caption.objects.filter(Qr) \
                  .count()
    else:
        icid = sid
        num_iid = num_sid
        if Qr is None:
            num_icid = Caption.objects.all().count()
        else:
            num_icid = Caption.objects.filter(Qr).count()

    return icid, num_iid, num_icid

def get_ans_gt_qsearch(ans_search_keep, all_true=False):

    Qr_a_s_k = None

    for key, val in ans_search_keep.items():
        if val or all_true:
            kwargs = {'{}'.format(ans_search_mapping[key]): True}
            q = Q(**kwargs)
            if Qr_a_s_k:
                # Change the '|' to '&' if want
                # search string to be in both
                Qr_a_s_k = Qr_a_s_k | q
            else:
                Qr_a_s_k = q

    return Qr_a_s_k

def qa_search(Image,
                Question, 
                Answer, 
                search_methods, 
                search_strs, 
                ans_types, 
                ans_search_keep, 
                sid, 
                num_sid):
# Assumes iqid is None or > 0 elements

    ques_search_str = search_strs['ques']
    str_ques_search = len(ques_search_str.strip()) != 0
    
    ans_search_str = search_strs['ans']
    str_ans_search = len(ans_search_str.strip()) != 0
    
    all_types = len(ans_types) == len(ans_type_mapping)

    all_questions = not str_ques_search and all_types

    Qr_a_s_k = get_ans_gt_qsearch(ans_search_keep)

    if Qr_a_s_k:

        if sid is not None:
            Qr_img = Q(image__in=sid)
        else:
            Qr_img = None

        Qr_ans = Qr_a_s_k

        if all_questions and not str_ans_search:
            if sid is None:
                num_iid = Image.objects.all().count()
                num_iqid = Question.objects.all().count()
                num_iqaid = Answer.objects.filter(Qr_ans) \
                        .count()
            else:
                num_iid = num_sid
                num_iqid = Question.objects.filter(Qr_img).count()
                num_iqaid = Answer.objects.filter(Qr_img & Qr_ans) \
                        .count()

            iqaid = sid
        else:
            if str_ans_search:
                kwargs = {'answer__{}'.format(search_methods['ans']): ans_search_str}
                q = Q(**kwargs)
                Qr_ans = Qr_ans & q
            
            if all_questions:

                if Qr_img is not None:
                    Qr_ans = Qr_ans & Qr_img

            else:

                Qr_ques = None

                if Qr_img:
                    if Qr_ques:
                        Qr_ques = Qr_ques & Qr_img
                    else:
                        Qr_ques = Qr_img

                if not all_types:
                    q = Q(ans_type__in=ans_types)
                    if Qr_ques:
                        Qr_ques = Qr_ques & q
                    else:
                        Qr_ques = Qr_img

                if str_ques_search:
                    kwargs = {'question__{}'.format(search_methods['ques']): ques_search_str}
                    q = Q(**kwargs)
                    if Qr_ques:
                        Qr_ques = Qr_ques & q
                    else:
                        Qr_ques = Qr_img

                sid = Question.objects \
                    .filter(Qr_ques) \
                    .values('ques_id')

                Qr_ans = Qr_ans & Q(ques_id__in=sid)

            num_iid = iqaid = Answer.objects.filter(Qr_ans) \
                    .values('image') \
                    .distinct() \
                    .count()
            num_iqid = Answer.objects.filter(Qr_ans) \
                    .values('ques_id') \
                    .distinct() \
                    .count()
            num_iqaid = Answer.objects.filter(Qr_ans) \
                    .count()
            iqaid = Answer.objects.filter(Qr_ans) \
                    .values('image') \
                    .distinct()

    else:
        iqaid = []
        num_iid = 0
        num_iqid = 0
        num_iqaid = 0

    return iqaid, num_iid, num_iqid, num_iqaid
