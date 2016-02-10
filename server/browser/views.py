import logging
import json
import random
from math import ceil
import time
import datetime
from copy import deepcopy

from redis import Redis

from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.db.models import Q

from config.settings import REDIS_PORT

from .models import URLBase, \
    ImageCOCO, ImageAS, \
    CategoryCOCO, CategoryAS, \
    AnnotationCOCO, AnnotationAS, \
    AnnotationCountCOCO, AnnotationCountAS, \
    CaptionCOCO, CaptionAS, \
    QuestionCOCO, QuestionAS, \
    AnswerCOCO, AnswerAS

r_server = Redis(host='redis', port=REDIS_PORT)
logger = logging.getLogger('django.request')

def generic_request_handler(request, data_get_process, data_post_process):
    
    resp = 'Default response.'

    if request.method == 'GET':
        response = data_get_process(request.GET)  
    elif request.method == 'POST':
        post_data = json.loads(request.POST['resp'])
        resp = data_post_process(post_data)
        response = HttpResponse(json.dumps(resp), 
                                content_type="application/json")

    response["Access-Control-Allow-Origin"] = "*"  
    response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"  
    response["Access-Control-Max-Age"] = "1000"  
    response["Access-Control-Allow-Headers"] = "*"  

    return response

@csrf_exempt
def categories(request):
    return generic_request_handler(request,
                                   categories_get_function,
                                   None)

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
def index(request):
    return generic_request_handler(request,
                                   index_get_function,
                                   None)

def index_get_function(get_data):

    if 'redis' in get_data:
        logger.error('Flushing Redis database.')
        r_server.flushdb()

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
        req_d['ansSearchKeep'] = {'gta': True, 
                                  'csa': False}

    req = index_get_ajax(req_d)
    resp = json.dumps(req)
    response = HttpResponse(resp,
                            content_type="application/json")

    return response

ans_type_mapping = {'binary': 'yes/no',
                    'number': 'number',
                    'other': 'other',
                    }

ans_search_mapping = {'gta': 'is_ans_img',
                      'csa': 'is_ans_no_img',
                    }

def ans_type_list(ques_search_keep):

    ans_types = [ans_type_mapping[t] 
                for t in ques_search_keep 
                    if ques_search_keep[t]]

    return ans_types

def index_get_ajax(param):

    EXPIRE_TIME = datetime.datetime.now() \
                  + datetime.timedelta(days=1, seconds=0)

    start = time.perf_counter()

    param_str = param_to_str(param)

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
        'curPage': cur_page,
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

    all_imgs = []
    cur_page_data = []
    num_pages = 0
    num_all_imgs = 0
    num_iqid = 0
    num_iqaid = 0
    num_icid = 0

    if len(ans_types) > 0:
        
        num_all_imgs = r_server.get('num_all_imgs-{}'.format(param_str))
        
        if not num_all_imgs:
            num_all_imgs = 0
            loaded = False

            iid, num_iid = object_search(Image,
                                        AnnotationCount,
                                        req_cat)

            if iid is None or num_iid > 0:                
                icid, num_iid, num_icid, _ = caption_search(Caption,
                                                search_methods['cap'],
                                                search_strs['cap'],
                                                iid,
                                                num_iid)

                if icid is None or num_iid > 0:
                    
                    iid, num_iid_new, num_iqid, num_iqaid, _ = \
                                                    qa_search(Image,
                                                            Question, 
                                                            Answer, 
                                                            search_methods, 
                                                            search_strs, 
                                                            ans_types, 
                                                            ans_search_keep, 
                                                            icid, 
                                                            num_iid)

                    if num_iid != num_iid_new:
                        if num_iid_new > 0:
                            iid, num_iid, num_icid, _ = \
                                                    caption_search(Caption,
                                                        search_methods['cap'],
                                                        search_strs['cap'],
                                                        iid,
                                                        num_iid_new)
                        else:
                            num_icid = 0
                            num_iid = 0

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

                    cur_page_data, num_pages = get_page_data(all_imgs,
                                            num_all_imgs,
                                            rand_seed,
                                            cur_page,
                                            max_imgs_page,
                                            show_all_data,
                                            search_methods, 
                                            search_strs, 
                                            ans_types, 
                                            ans_search_keep,
                                            Image,
                                            Caption,
                                            Question,
                                            Answer)
        else:
            loaded = True
            num_all_imgs = int(num_all_imgs)
            all_imgs = r_server.lrange('all_imgs-{}'.format(param_str), 0, -1)
            num_iqid = int(r_server.get('num_iqid-{}'.format(param_str)))
            num_iqaid = int(r_server.get('num_iqaid-{}'.format(param_str)))
            num_icid = int(r_server.get('num_icid-{}'.format(param_str)))
            
            r_server.expireat('all_imgs-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.expireat('num_all_imgs-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.expireat('num_iqid-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.expireat('num_iqaid-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.expireat('num_icid-{}'.format(param_str),
                                EXPIRE_TIME)

            cur_page_data, num_pages = get_page_data(all_imgs,
                                            num_all_imgs,
                                            rand_seed,
                                            cur_page,
                                            max_imgs_page,
                                            show_all_data,
                                            search_methods, 
                                            search_strs, 
                                            ans_types, 
                                            ans_search_keep,
                                            Image,
                                            Caption,
                                            Question,
                                            Answer)
        if not loaded:
            if num_all_imgs > 0:
                r_server.rpush('all_imgs-{}'.format(param_str),
                                *all_imgs)
                r_server.expireat('all_imgs-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.set('num_all_imgs-{}'.format(param_str),
                            num_all_imgs)
            r_server.expireat('num_all_imgs-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.set('num_iqid-{}'.format(param_str),
                            num_iqid)
            r_server.expireat('num_iqid-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.set('num_iqaid-{}'.format(param_str),
                            num_iqaid)
            r_server.expireat('num_iqaid-{}'.format(param_str),
                                EXPIRE_TIME)
            r_server.set('num_icid-{}'.format(param_str),
                            num_icid)
            r_server.expireat('num_icid-{}'.format(param_str),
                                EXPIRE_TIME)

    resp['curPageData'] = cur_page_data
    resp['numPages'] = num_pages
    resp['numSearchImgs'] = num_all_imgs
    resp['numSearchQs'] = num_iqid
    resp['numSearchAs'] = num_iqaid
    resp['numSearchCaps'] = num_icid

    # Cache/load these
    data_names = ['numTotalImgs', 
                  'numTotalQs',
                  'numTotalAs',
                  'numTotalCaps'
                  ]
    
    for data_name in data_names:
        name = dataset + '-' + data_name
        if data_name == 'numTotalAs':
            name += '-' + str(ans_search_keep['gta'])
            name += '-' + str(ans_search_keep['csa'])
        
        r_val = r_server.get(name)        
        if not r_val:
            if data_name == 'numTotalImgs':
                val = Image.objects.all().count() 
            elif data_name == 'numTotalQs':
                val = Question.objects.all().count()
            elif data_name == 'numTotalAs':
                if len(search_strs['ans'].strip()) != 0:
                    Qr = get_ans_gt_qsearch(ans_search_keep)
                else:
                    Qr = get_ans_gt_qsearch(ans_search_keep,
                                            all_true=True)
                val = Answer.objects.filter(Qr).count()
            elif data_name == 'numTotalCaps':
                val = Caption.objects.all().count()

            r_server.set(name, val)
            r_server.expireat(name,
                            EXPIRE_TIME)

        resp[data_name] = int(r_server.get(name))

    total = time.perf_counter() - start
    logger.error('Response Time: {} s'.format(total))

    return resp

def param_to_str(param):
    
    new_param = deepcopy(param)
    
    del new_param['showAllDataEachImg']
    del new_param['curPage']
    del new_param['maxImgsPerPage']
    
    param_str = json.dumps(new_param)
    
    return param_str

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
                   num_sid,
                   ret_cap_ids=False):
# Assumes sid is None or > 0 elements

    cid = None

    if sid:
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
        if ret_cap_ids:
            cid = Caption.objects.filter(Qr) \
                  .order_by('cap_id').values('caption', 'cap_id')
    else:
        icid = sid
        num_iid = num_sid
        if Qr is None:
            num_icid = Caption.objects.all().count()
            if ret_cap_ids:
                cid = Caption.objects.all() \
                      .order_by('cap_id') \
                      .values('caption', 'cap_id')
        else:
            num_icid = Caption.objects.filter(Qr).count()
            if ret_cap_ids:
                cid = Caption.objects.filter(Qr) \
                      .order_by('cap_id') \
                      .values('caption', 'cap_id')

    return icid, num_iid, num_icid, cid

def qa_search(Image,
                Question, 
                Answer, 
                search_methods, 
                search_strs, 
                ans_types, 
                ans_search_keep, 
                sid, 
                num_sid,
                ret_qa_ids=False):
# Assumes iqid is None or > 0 elements

    aid = None

    ques_search_str = search_strs['ques']
    str_ques_search = len(ques_search_str.strip()) != 0
    
    ans_search_str = search_strs['ans']
    str_ans_search = len(ans_search_str.strip()) != 0
    
    all_types = len(ans_types) == len(ans_type_mapping)

    all_questions = not str_ques_search and all_types

    if str_ans_search:
        Qr_a_s_k = get_ans_gt_qsearch(ans_search_keep)
    else:
        Qr_a_s_k = get_ans_gt_qsearch(ans_search_keep,
                                      all_true=True)

    if Qr_a_s_k:

        if sid:
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
                if ret_qa_ids:
                    aid = Answer.objects.filter(Qr_ans) \
                        .order_by('ques_id', 'ans_num')
            else:
                num_iid = num_sid
                num_iqid = Question.objects.filter(Qr_img).count()
                num_iqaid = Answer.objects.filter(Qr_img & Qr_ans) \
                        .count()
                if ret_qa_ids:
                    aid = Answer.objects.filter(Qr_img & Qr_ans) \
                        .order_by('ques_id', 'ans_num')
            iqaid = sid
        else:
            if str_ans_search:
                kwargs = {'answer__{}'.format(search_methods['ans']): 
                              ans_search_str}
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
                        Qr_ques = q

                if str_ques_search:
                    kwargs = {'question__{}'.format(search_methods['ques']): 
                                  ques_search_str}
                    q = Q(**kwargs)
                    if Qr_ques:
                        Qr_ques = Qr_ques & q
                    else:
                        Qr_ques = q

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
                
            if ret_qa_ids:
                aid = Answer.objects.filter(Qr_ans) \
                    .order_by('ques_id', 'ans_num')
    else:
        iqaid = []
        num_iid = 0
        num_iqid = 0
        num_iqaid = 0

    return iqaid, num_iid, num_iqid, num_iqaid, aid

def get_page_data(all_imgs,
                  num_all_imgs,
                  rand_seed,
                  cur_page,
                  max_imgs_page,
                  show_all_data,
                  search_methods, 
                  search_strs, 
                  ans_types, 
                  ans_search_keep,
                  Image,
                  Caption,
                  Question,
                  Answer):
    
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

    if rand_seed >= 0:
        final_imgs = Image.objects.filter(image_id__in=imgs)
    else:
        final_imgs = Image.objects.filter(image_id__in=imgs) \
                     .order_by('image_id')

    data = []
    
    for idx, d in enumerate(final_imgs):
        img_obj = { 'img': d.image_name,
                    'imgID': d.image_id,
                    'url': d.get_url(),
                    'uniqueIndex': idxs[idx]+1,
                    'questions': [],
                    'captions': [],
                    }
        
        if show_all_data:
            
            caps = Caption.objects.filter(image=d) \
                   .order_by('cap_id').values('caption', 'cap_id')
            img_obj['captions'] = [{'caption': c['caption'],
                                    'cap_id':c['cap_id']} for c in caps]
            
            questions = []
            anss = Answer.objects.filter(image=d) \
                   .order_by('ques_id', 'ans_num')
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
                    q_obj['ansImg'].append({'ansNum': ans.ans_num,
                                            'ansStr': ans.answer})
                elif ans.is_ans_no_img:
                    q_obj['ansNoImg'].append({'ansNum': ans.ans_num,
                                              'ansStr': ans.answer})
                elif ans.is_ans_mc_img:
                    q_obj['ansMCImg'] = json.loads(ans.answer)

            img_obj['questions'] = questions
        else:
            
            _, _, _, caps = caption_search(Caption,
                                                search_methods['cap'],
                                                search_strs['cap'],
                                                [d],
                                                1,
                                                ret_cap_ids=True)
            img_obj['captions'] = [{'caption': c['caption'],
                                    'cap_id':c['cap_id']} for c in caps]
            
            _, _, _, _, anss = qa_search(Image,
                                            Question, 
                                            Answer, 
                                            search_methods, 
                                            search_strs, 
                                            ans_types, 
                                            ans_search_keep, 
                                            [d], 
                                            1,
                                            ret_qa_ids=True)
            questions = []
            ques_id_old = -1
            for ans in anss:
                ques_id = ans.ques_id
                if ques_id != ques_id_old:
                    ques_id_old = ques_id
                    q = Question.objects.get(ques_id=ques_id)
                    mc_list = json.loads(Answer.objects \
                                         .get(ques_id=ques_id,
                                              is_ans_mc_img=True).answer)
                    q_obj = { 'quesStr': q.question,
                            'quesID': q.ques_id,
                            'quesType': q.ques_type,
                            'ansType': q.ans_type,
                            'ansMCImg': mc_list,
                            'ansImg': [],
                            'ansNoImg': [],
                        }
                    questions.append(q_obj)
                if ans.is_ans_img:
                    q_obj['ansImg'].append({'ansNum': ans.ans_num, 
                                            'ansStr': ans.answer})
                elif ans.is_ans_no_img:
                    q_obj['ansNoImg'].append({'ansNum': ans.ans_num, 
                                              'ansStr': ans.answer})
                
            img_obj['questions'] = questions
        data.append(img_obj)
            
    return data, num_pages

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
