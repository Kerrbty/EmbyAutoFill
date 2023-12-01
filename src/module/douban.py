#!/usr/bin/python
# -*- coding: UTF-8 -*- 

import os,sys
import re
import yaml
import time
import json

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, '..'))
sys.path.append(root_dir)
html_tmp_path = os.path.join(root_dir, 'data', 'descript')
from module.comm import logger, get_html, post_html, get_content
import module.sql

http_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
}
with open(os.path.join(root_dir, 'config', 'config.yaml'), 'r') as config:
    __emby_cfg__ = yaml.safe_load(config)
    __douban_cookie__ = __emby_cfg__['douban']['cookie']
    http_headers['Cookie'] = __douban_cookie__
if not os.path.exists(html_tmp_path):
    os.makedirs(html_tmp_path)

# 获取电影名 和 年份 
def get_name_year(html):
    title = None
    year = '1800'
    # 方法一: 
    title_list = re.findall(r'property="v:itemreviewed">(.*?)</span>', html)
    year_list = re.findall(r'class="year">\((\d+)\)</span>', html)
    if len(title_list)>0:
        title = title_list[0]
    if len(year_list)>0:
        year = year_list[0]
    # 方法二: 
    if not title or not year:
        htitle = re.findall(r'type="hidden" name="title" value="(.*?)\((\d+)\)', html)
        if len(htitle)>0:
            title, year = htitle[0]
            title = title.replace('\u200e', '')
    # 方法三: 
    if not title or not year:
        htitle = re.findall(r'<strong>(.*?)\((\d+)\)</strong>', html)
        if len(htitle)>0:
            title, year = htitle[0]
    # 方法四: 
    if not title or not year:
        htitle = re.findall(r'data-name="(.*?)\((\d+)\)"', html)
        if len(htitle)>0:
            title, year = htitle[0]
    # 方法五：
    if year == '1800':
        years_list = re.findall(r'property="v:initialReleaseDate" content="(\d+)">(\d+)</span>', html)
        if len(years_list)>0:
            year = years_list[0][0]
    title = title.replace('\u200e', '')
    year = year.replace('２', '2').replace('１', '1').replace('０', '0')
    return title, int(year)

def get_celebrity_name(html):
    html = html.replace('\r', '').replace('\n', '')
    hideTitles = re.findall(r'name="title" value="(.*?)">', html)
    if len(hideTitles)>0:
        return hideTitles[0].strip()
    dataTitles = re.findall(r'data-title="(.*?)"', html)
    if len(dataTitles)>0:
        return dataTitles[-1].strip()
    titles = re.findall(r'<title>(.*?)</title>', html)
    if len(titles)>0:
        return titles[0].strip()
    strongs = re.findall(r'<h1>(.*?)</h1>', html)
    if len(strongs)>0:
        return strongs[0].strip()

def get_short_celebrity_name(html):
    ogtitle = re.findall(r'property="og:title" content="(.*?)"', html)
    if len(ogtitle)>0:
        return ogtitle[0].strip()
    return get_celebrity_name(html)

# 获取电影别名 
def get_alias(html):
    aliasList = []
    alias_list = re.findall(r'又名:</span>(.*?)<br/>', html)
    if len(alias_list)>0:
        alias_sp = alias_list[0].split('/')
        for i in alias_sp:
            aliasList.append(i.strip())
        return aliasList
    return ['']

# 获取电影海报 
def get_poster(html):
    poster_list = re.findall(r'src="(.*?)" title="点击看更多海报"', html)
    if len(poster_list)>0:
        poster = poster_list[0]
        return poster.replace('s_ratio_poster', 'l')
    image_list = re.findall(r'"image": "(.*?)",', html)
    if len(image_list)>0:
        poster = image_list[0]
        return poster.replace('s_ratio_poster', 'l')
    return ''
def get_poster2(html):
    poster_list = re.findall(r'property="og:image" content="(.*?)"', html)
    if len(poster_list)>0:
        poster = poster_list[0]
        return poster.replace('s_ratio_poster', 'l')
    image_list = re.findall(r'data-picture="(.*?)"', html)
    if len(image_list)>0:
        poster = image_list[0]
        return poster.replace('s_ratio_poster', 'l')
    return ''

# IMDb id 
def get_imdb(html):
    imbi_list = re.findall(r'IMDb:</span>(.*?)<br>', html)
    if len(imbi_list)>0:
        return imbi_list[0].strip()
    return ''
def get_imdb2(html):
    imdblist = re.findall(r'https://www\.imdb\.com/name/(.*?)"', html)
    if len(imdblist)>0:
        return imdblist[0]
    return ''

# 上映日期 
def get_date(html):
    date_list = re.findall(r'property="v:initialReleaseDate" content="(.*?)"', html)
    if len(date_list)>0:
        year_data = date_list[0].split('(')
        return year_data[0]
    datePublished = re.findall(r'"datePublished": "(.*?)",', html)
    if len(datePublished)>0:
        return datePublished[0]
    return ''

# 得分(star星评/value十分制/count评价人数)
def get_rating(html):
    # 得分 / 评价人数 / 星评 
    rating = {'value': '0', 'count': '0', 'star': '0'}
    aggregateRating = re.findall(r'("aggregateRating": {[^}]*})', html)
    if len(aggregateRating) > 0:
        json_rate = json.loads('{' + aggregateRating[0] + '}')
        rating['count'] = json_rate['aggregateRating']['ratingCount']
        rating['value'] = json_rate['aggregateRating']['ratingValue']
    bigstar = re.findall(r'bigstar(\d+)', html)
    if len(bigstar)>0:
        rating['star'] = int(bigstar[0])/10
    if rating['count'] == '0':
        votes_list = re.findall(r'property="v:votes">(\d+)</span>', html)
        if len(votes_list)>0:
            rating['count'] = votes_list[0]
    if rating['value'] == '0': 
        average_list = re.findall(r'property="v:average">(.*?)</strong>', html)
        if len(average_list)>0:
            rating['value'] = average_list[0]
    # 五星占比 rating['star']
    return str(rating['value'])

# 制片国家 
def get_counrty(html):
    country_list = re.findall(r'制片国家/地区:</span>(.*?)<br/>', html)
    if len(country_list)>0:
        return [country_list[0].strip()]
    return ['']
def get_birth(html):
    pagehtml = html.replace('\r', '').replace('\n', '').replace(' ', '')
    birth_place = re.findall(r'<span>出生地</span>:(.*?)</li>', pagehtml)
    if len(birth_place) > 0:
        return birth_place[0].split('，')
    return []

# 类型风格 
def get_genres(html):
    genresList = []
    type_list = re.findall(r'property="v:genre">(.*?)</span>', html)
    for i in type_list:
        genresList.append(i.strip())
    return genresList
# 标签 
def get_tags(html):
    tagsList = []
    country_list = re.findall(r'制片国家/地区:</span>(.*?)<br/>', html)
    if len(country_list)>0:
        tagsList.append(country_list[0].strip())
    language_list = re.findall(r'语言:</span>(.*?)<br/>', html)
    if len(language_list)>0:
        tagsList.append(language_list[0].strip())
    return tagsList
def get_tags2(html):
    tagsList = []
    pagehtml = html.replace('\r', '').replace('\n', '').replace(' ', '')
    jobs_list = re.findall(r'<span>职业</span>:([\w/]+)</li>', pagehtml)
    if len(jobs_list)>0:
        for i in jobs_list[0].split('/'):
            tagsList.append(i.strip())
    return tagsList

# 演员列表 
def _get_director(html):
    roteList = []
    directors = re.findall(r'"director":\s+\[([^\x5d]*?)\]', html)
    if len(directors)>0:
        name_list = re.findall(r'"name": "(.*?)"', directors[0])
        roteid_list = re.findall(r'/celebrity/(\d+)/', directors[0])
        for index in range(len(name_list)):
            roteList.append({'Name':roteid_list[index], 'Type':'Director'})
            break
        return roteList
    director_list = re.findall(r'property="video:director" content="(.*?)"', html)
    if len(director_list)>0:
        for name in director_list:
            roteList.append({'Name':name, 'Type':'Director'})
            break
        return roteList 
    directedBy_list = re.findall(r'href="/celebrity/(\d+)/" rel="v:directedBy">(.*?)</a>', html)
    if len(directedBy_list)>0:
        for id, name in directedBy_list:
            roteList.append({'Name':id, 'Type':'Director'})
            break
        return roteList 
    return roteList
def _get_author(html):
    roteList = []
    indexCount = 3
    directors = re.findall(r'"author":\s+\[([^\x5d]*?)\]', html)
    if len(directors)>0:
        name_list = re.findall(r'"name": "(.*?)"', directors[0])
        roteid_list = re.findall(r'/celebrity/(\d+)/', directors[0])
        for index in range(len(name_list)):
            indexCount = indexCount - 1
            if indexCount == 0:
                break
            roteList.append({'Name':roteid_list[index], 'Type':'Writer'})
        return roteList
    return roteList
def _get_actors(html):
    roteList = []
    actors = re.findall(r'"actor":\s+\[([^\x5d]*?)\]', html)
    indexCount = 7
    if len(actors)>0:
        name_list = re.findall(r'"name": "(.*?)"', actors[0])
        roteid_list = re.findall(r'/celebrity/(\d+)/', actors[0])
        for index in range(len(name_list)):
            indexCount = indexCount -1
            if indexCount == 0:
                break
            roteList.append({'Name':roteid_list[index], 'Type':'Actor'})
        return roteList
    actor_list = re.findall(r'property="video:actor" content="(.*?)"', html)
    if len(actor_list)>0:
        for name in actor_list:
            indexCount = indexCount -1
            if indexCount == 0:
                break
            roteList.append({'Name':name, 'Type':'Actor'})
        return roteList 
    starring_list = re.findall(r'href="/celebrity/(/d)/" rel="v:starring">(.*?)</a>', html)
    if len(starring_list)>0:
        for id, name in starring_list:
            indexCount = indexCount -1
            if indexCount == 0:
                break
            roteList.append({'Name':id, 'Type':'Actor'})
        return roteList 
    return roteList
def get_rotes(html):
    roteList = _get_director(html)
    roteList += _get_author(html)
    roteList += _get_actors(html)
    return roteList

# 影视简介 
def __get_descript__(html):
    hidden_desp = re.findall(r'class="all hidden"[^>]*>([\w|\W]*?)</span>', html)
    if len(hidden_desp)>0:
        desc0 = hidden_desp[0].replace(' ', '').replace('\n', '').replace('\r', '')
        return desc0
    descripts = re.findall(r'property="v:summary"[^>]*>([\w|\W]*?)</span>', html)
    if len(descripts)>0:
        desc = descripts[0].replace(' ', '').replace('\n', '').replace('\r', '')
        return desc
    descripts2 = re.findall(r'"description": ".*?",', html)
    if len(descripts2)>0:
        return descripts2[0]
    descripts3 = re.findall(r'property="og:description" content="([\w|\W]*?)"', html)
    if len(descripts3)>0:
        return descripts3[0]
def get_descript(html):
    desp = '&emsp;&emsp;' + __get_descript__(html)
    return desp.replace('  ', '&emsp;').replace('"', '&quot;')

# 从缓存或者网上更新页面(抛出异常表示禁止访问，IP被限制) 
def _get_page_(url, tmp_path, force = False):
    pagehtml = None
    # 是否强制更新文件 
    if force and os.path.exists(tmp_path):
        os.remove(tmp_path)
    # 如果已经有缓存，使用缓存，如果没有下载电影信息 
    if os.path.exists(tmp_path):
        with open(tmp_path, 'rb') as fp:
            pagehtml = fp.read().decode('utf-8')
    else:
        pagehtml = get_html(url, headers = http_headers)
        # 空页面不记录文件 
        if pagehtml:
            with open(tmp_path, 'wb') as fp:
                fp.write(pagehtml.encode('utf-8'))
        else:
            raise Exception('page empty.') 
    # 检测电影是否存在  
    title = re.findall(r'<title>([\w|\W]*?)</title>', pagehtml)
    if len(title)>0:
        if title[0].strip()=='页面不存在' or title[0].strip()=='条目不存在':
            # 不存在的页面需要删除 
            os.remove(tmp_path)
            return None,0
        elif title[0].strip()=='豆瓣 - 登录跳转页':
            ids_page = re.findall(r'%2Fsubject%2F(\d+)%2F', pagehtml)
            if len(ids_page)>0:
                # 跳转的页面需要删除 
                os.remove(tmp_path)
                return None,ids_page[0]
            return None,0
        elif title[0].strip()=='禁止访问':
            # IP被禁的页面需要删除 
            os.remove(tmp_path)
            raise Exception('禁止访问.') 
    else:
        # 条目不存在的另一种形式 
        if re.match(r'^<script>var d=\[navigator.platform', pagehtml):
            # 跳转的页面需要删除 
            os.remove(tmp_path)
            return None,0
    return pagehtml,0

def get_page(url, tmp_path, force = False):
    while True:
        try:
            return _get_page_(url, tmp_path, force)
        except:
            # 打开默认浏览器验证非机器人 
            os.system('start ' + url)
            time.sleep(15)

definition = ['4k', '4K', '1080P', '1080p', '720p', '720P', '8k', '8K', '3D', '3d']
def split_keywork(str):
    key_words = []
    year = 0
    tmp_split = str.replace(' ', '.').replace(',', '.').split('.')
    for i in tmp_split:
        if i in definition:
            continue
        elif re.match('^\d{4}$', i):
            if year != 0:
                key_words.append(str(year))
            year = int(i)
        else:
            key_words.append(i)
    return key_words, year

def get_douban_id(name):
    key_words, year = split_keywork(name)
    movie_obj = module.sql.movie()
    databases = movie_obj.search_movie_by_name(key_words[0])
    find_index = 0
    # 搜索结果进行排序 
    search_result = []
    for data in databases:
        # 多个关键字搜索 
        if len(key_words) > 1:
            for index in range(1, len(key_words)):
                if key_words[index] in data[1] or key_words[index] in data[2]:
                    search_result.append(data)
                    # 年代一致，插入首位 
                    if year>1800:
                        if len(search_result)>1:
                            if year==data[4] or str(year) in data[5]:
                                search_result[find_index], search_result[-1] = search_result[-1], search_result[find_index]
                                find_index = find_index + 1
                    break
        # 只有一个关键字 
        else:
            search_result.append(data)
            if year>1800:
                if len(search_result)>1:
                    if year==data[4] or str(year) in data[5]:
                        search_result[find_index], search_result[-1] = search_result[-1], search_result[find_index]
                        find_index = find_index + 1
    if len(search_result) > 0:
        return search_result[0][0]
    return 0


def update_media_with_douban(mediaInfo, imageList = None, updateFunc = None, forceUpdate = False):
    doubanId = ''
    # 优先使用已填入的doubanId，数据库搜索毕竟不准确 
    if 'ProviderIds' in mediaInfo and 'DoubanID' in mediaInfo['ProviderIds']:
        doubanId = mediaInfo['ProviderIds']['DoubanID']
    if not doubanId:
        orgTitle = mediaInfo['Name']
        doubanId = get_douban_id(orgTitle)
    if not doubanId:
        return False
    # 下载最新页面 
    movie_url = 'https://movie.douban.com/subject/{}/'.format(doubanId)
    cached_file_name = os.path.join(html_tmp_path, 'subject_'+str(doubanId)+'.html')
    pagehtml,jmp_id = get_page(movie_url, cached_file_name)
    # 获取数据 
    rName, rYear = get_name_year(pagehtml)
    mediaInfo['Name'] = rName
    mediaInfo['ForcedSortName'] = mediaInfo['SortName'] = get_alias(pagehtml)[0]
    mediaInfo['CommunityRating'] = get_rating(pagehtml)
    mediaInfo['Overview'] = get_descript(pagehtml)
    mediaInfo['Genres'] = get_genres(pagehtml)
    mediaInfo['Tags'] = get_tags(pagehtml)
    mediaInfo['TagItems'] = []
    for tag in mediaInfo['Tags']:
        mediaInfo['TagItems'].append({'Name': tag})
    mediaInfo['PremiereDate'] = get_date(pagehtml)
    mediaInfo['ProductionYear'] = rYear
    mediaInfo['People'] = get_rotes(pagehtml) # 角色先用需要编码，后面再更新 
    mediaInfo['ProviderIds']['Imdb'] = get_imdb(pagehtml)
    mediaInfo['ProviderIds']['DoubanID'] = doubanId
    mediaInfo['LockData'] = True
    mediaInfo['LockedFields'] = ["Name","OriginalTitle","SortName","CommunityRating","CriticRating","Tagline","Overview","OfficialRating","Genres","Studios","Tags"] 
    poster_img = get_poster(pagehtml)
    if forceUpdate or not imageList or not 'Primary' in imageList:
        if updateFunc:
            logger('upload', poster_img)
            imgbin = get_content(poster_img, http_headers)
            updateFunc(mediaInfo['Id'], 'Primary', imgbin)
    return True


def update_role_with_douban(roleInfo, imageList = None, updateFunc = None, forceUpdate = False):
    if re.match(r'\d+', roleInfo['Name']):
        roleId = roleInfo['Name']
        role_url = 'https://movie.douban.com/celebrity/{}/'.format(roleId)
        cached_file_name = os.path.join(html_tmp_path, 'celebrity_'+str(roleId)+'.html')
        pagehtml,jmp_id = get_page(role_url, cached_file_name)
        logger(role_url)
        if pagehtml:
            roleInfo['Name'] = get_celebrity_name(pagehtml)
            roleInfo['SortName'] = roleInfo['ForcedSortName'] = get_short_celebrity_name(pagehtml)
            roleInfo['Overview'] = get_descript(pagehtml)
            roleInfo['ProviderIds']['Imdb'] = get_imdb2(pagehtml)
            roleInfo['ProviderIds']['Tvdb'] = str(roleId) # tvdb 存下豆瓣id 
            roleInfo['Tags'] = get_tags2(pagehtml)
            roleInfo['TagItems'] = []
            for tag in roleInfo['Tags']:
                roleInfo['TagItems'].append({'Name': tag})
            roleInfo['ProductionLocations'] = get_birth(pagehtml)
            roleInfo['LockData'] = True
            roleInfo['LockedFields'] = ["Name", "SortName", "Overview", "Tags"]
            poster_img = get_poster2(pagehtml)
            if forceUpdate or not imageList or not 'Primary' in imageList:
                if updateFunc:
                    logger('upload', poster_img)
                    imgbin = get_content(poster_img, http_headers)
                    updateFunc(roleInfo['Id'], 'Primary', imgbin)
            return True
    return False



if __name__=="__main__":
    doubanId = 1321964
    movie_url = 'https://movie.douban.com/celebrity/{}/'.format(doubanId)
    cached_file_name = os.path.join(html_tmp_path, 'celebrity_'+str(doubanId)+'.html')
    pagehtml,jmp_id = get_page(movie_url, cached_file_name)

    # print(get_tags2(pagehtml)) # Tags / TagItems 
    # print(get_birth(pagehtml)) # ProductionLocations
    # print(get_imdb2(pagehtml)) # ProviderIds['Imdb']
    # print(get_descript(pagehtml)) # Overview 
    print(get_celebrity_name(pagehtml)) # Name 
    print(get_short_celebrity_name(pagehtml)) # SortName /ForcedSortName 
    print(get_poster2(pagehtml))

