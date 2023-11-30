#!/usr/bin/python
# -*- coding: UTF-8 -*- 

import os,sys
import requests
import json
import base64
import yaml

cur_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, '..'))
sys.path.append(root_dir)
from module.comm import logger, get_html, post_html, get_content

# 读emby配置 
with open(os.path.join(root_dir, 'config', 'config.yaml'), 'r') as config:
    cfg = yaml.safe_load(config)
    host_name = cfg['emby']['host']
    api_key = cfg['emby']['apikey']

json_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
    'Content-Type': 'text/plain',
    'Accept': '*/*'
}

image_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
    'Content-Type': 'image/jpg',
    'Accept': '*/*'
}

def get_users():
    """
    获取所有用户 
    """
    userList = []
    req_url = '{0}/Users?api_key={1}'.format(host_name, api_key)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for jvUser in jvData:
            userInfo = {}
            userInfo['name'] = jvUser['Name']
            userInfo['id'] = jvUser['Id']
            userInfo['admin'] = jvUser['Policy']['IsAdministrator']
            userList.append(userInfo)
    return userList


def get_media_library(userId = None):
    """
    获取指定用户的所有媒体库 
    """
    LibraryList = []
    if userId:
        req_url = '{0}/emby/Users/{1}/Items?api_key={2}'.format(host_name, userId, api_key)
    else:
        req_url = '{0}/emby/Items?api_key={1}'.format(host_name, api_key)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for jvItem in jvData['Items']:
            # 略过直播 
            if jvItem['Type'] == 'UserView':
                continue
            # 其他媒体库 
            mediaInfo = {}
            mediaInfo['name'] = jvItem['Name']
            mediaInfo['id'] = jvItem['Id']
            if 'CollectionType' in jvItem and jvItem['CollectionType'] == 'movies':
                mediaInfo['movie'] = True
            else:
                mediaInfo['movie'] = False
            LibraryList.append(mediaInfo)
    return LibraryList


def get_media_items(libraryId, userId = None):
    """
    获取媒体库里面所有影片 
    """
    mediaList = []
    nIndex = 0
    while True:
        # 不同参数访问不同的列表 
        if userId:
            req_url = '{0}/emby/Items?ParentId={2}&SortBy=SortName&StartIndex={3}&Limit=50&api_key={4}'.format(host_name, userId, libraryId, nIndex, api_key)
        else:
            req_url = '{0}/emby/Users/{1}/Items?ParentId={2}&SortBy=SortName&StartIndex={3}&Limit=50&api_key={4}'.format(host_name, userId, libraryId, nIndex, api_key)
        # 获取到json数据 
        jsonStr = get_html(req_url)
        if not jsonStr:
            break
        jvData = json.loads(jsonStr)
        for item in jvData['Items']:
            mediaInfo = {}
            mediaInfo['name'] = item['Name']
            mediaInfo['id'] = item['Id']
            mediaList.append(mediaInfo)
        # 没满50个,说明已经到尾了 
        if jvData['TotalRecordCount'] < 50:
            break
        nIndex += 50
    return mediaList


def get_media_details(mediaId, userId):
    """
    获取影片已经设置的信息  
    """
    mediaDetails = {}
    req_url = '{0}/emby/Users/{1}/Items/{2}?api_key={3}'.format(host_name, userId, mediaId, api_key)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        mediaDetails['Id'] = jvData['Id']
        mediaDetails['Name'] = jvData['Name'] if 'Name' in jvData else '' # 标题 
        mediaDetails['ChannelNumber'] = ''
        mediaDetails['OriginalTitle'] = jvData['OriginalTitle'] if 'OriginalTitle' in jvData else '' # 原标题 
        mediaDetails['ForcedSortName'] = jvData['ForcedSortName'] if 'ForcedSortName' in jvData else '' # 类标题 
        mediaDetails['SortName'] = jvData['SortName'] if 'SortName' in jvData else '' # 类标题2
        mediaDetails['CommunityRating'] = str(jvData['CommunityRating']) if 'CommunityRating' in jvData else '' # 公众评分 
        mediaDetails['CriticRating'] = str(jvData['CriticRating']) if 'CriticRating' in jvData else '' # 影评人评分 
        mediaDetails['IndexNumber'] = None
        mediaDetails['ParentIndexNumber'] = None
        mediaDetails['SortParentIndexNumber'] = ''
        mediaDetails['SortIndexNumber'] = ''
        mediaDetails['DisplayOrder'] = jvData['DisplayOrder'] if 'DisplayOrder' in jvData else 'aired' # 显示顺序(aired/absolute/dvd)已播/独立/dvd 
        mediaDetails['Album'] = ''
        mediaDetails['AlbumArtists'] = []
        mediaDetails['ArtistItems'] = []
        mediaDetails['Overview'] = jvData['Overview'] if 'Overview' in jvData else '' # 描述信息 
        mediaDetails['Status'] = jvData['Status'] if 'Status' in jvData else 'Ended' # 状态 Continuing/Ended
        mediaDetails['Genres'] = jvData['Genres'] if 'Genres' in jvData else [] # 风格 ['风格1', '风格2']
        mediaDetails['TagItems'] = jvData['TagItems'] if 'TagItems' in jvData else [] # 标签列表 [{'name': '标签', 'Id': 4077}]
        mediaDetails['Tags'] = []
        for tag in mediaDetails['TagItems']:
            mediaDetails['Tags'].append(tag['Name']) 
        mediaDetails['TagItems'] = []
        for name in mediaDetails['Tags']:
            mediaDetails['TagItems'].append({'Name': name})
        StudioList = jvData['Studios'] if 'Studios' in jvData else [] # 工作室 [{"Name":"工作室1", 'Id': 4076}]
        mediaDetails['Studios'] = []
        for i in StudioList:
            mediaDetails['Studios'].append({'Name': i['Name']})
        mediaDetails['DateCreated'] = jvData['DateCreated'] if 'DateCreated' in jvData else '' # 加入时间 
        mediaDetails['ProductionYear'] = jvData['ProductionYear'] if 'ProductionYear' in jvData else '' # 年份 
        mediaDetails['Video3DFormat'] = ''  
        mediaDetails['OfficialRating'] = jvData['OfficialRating'] if 'OfficialRating' in jvData else '' # 家长分级 
        mediaDetails['CustomRating'] = jvData['CustomRating'] if 'CustomRating' in jvData else '' # 自定义分级 
        # 添加 {'Name':'伊峥', 'Role': None, 'Type': 'Director'} # Director 导演 , Actor 演员， GuestStar 特邀明星, Producer 纸片人,  Writer 编剧 
        mediaDetails['People'] = jvData['People'] if 'People' in jvData else [] # 人物列表 [{"Name":"Steven Zhang","Id":"904","Type":"Actor"}]
        mediaDetails['LockData'] = jvData['LockData'] if 'LockData' in jvData else True # 锁定此项目以防止被改动 
        mediaDetails['LockedFields'] = jvData['LockedFields'] if 'LockedFields' in jvData else ["Name","OriginalTitle","SortName","CommunityRating","CriticRating","Tagline","Overview","OfficialRating","Genres","Studios","Tags"] # 锁定项目列表 
        mediaDetails['ProviderIds'] = jvData['ProviderIds'] if 'ProviderIds' in jvData else {'DoubanID':'','Imdb':'','Tmdb':'','Tvdb':'','Zap2It':''} # 外部Ids列表  
        mediaDetails['PreferredMetadataLanguage'] = jvData['PreferredMetadataLanguage'] if 'PreferredMetadataLanguage' in jvData else 'zh-CN' # 首选元数据下载语言 
        mediaDetails['PreferredMetadataCountryCode'] = jvData['PreferredMetadataCountryCode'] if 'PreferredMetadataCountryCode' in jvData else 'CN' # 国家 
        mediaDetails['RunTimeTicks'] = jvData['RunTimeTicks'] if 'RunTimeTicks' in jvData else 0 
        mediaDetails['Taglines'] = jvData['Taglines'] if 'Taglines' in jvData else [] # 口号列表 
        # 标题和类标题不能为空的 
        if mediaDetails['Name'] == '':
            mediaDetails['Name'] = jvData['FileName']
        if mediaDetails['ForcedSortName'] == '':
            mediaDetails['ForcedSortName'] = jvData['FileName']
        if mediaDetails['SortName'] == '':
            mediaDetails['SortName'] = jvData['FileName']
    return mediaDetails


def set_media_details(mediaId, jsonStr):
    req_url = '{0}/emby/Items/{1}?reqformat=json&api_key={2}'.format(host_name, mediaId, api_key)
    ret_data = post_html(url=req_url, data=jsonStr.encode("utf-8").decode("latin1"), retry=1, headers=json_headers)
    if ret_data == '':
        return True
    if ret_data == None:
        return False


def get_media_images(mediaId):
    imageList = []
    req_url = '{0}/emby/Items/{1}/Images?api_key={2}'.format(host_name, mediaId, api_key)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for item in jvData:
            imageList.append(item['ImageType'])
    return imageList


def set_media_image(mediaId, imageType, filePath):
    if not os.path.exists(filePath):
        return False
    image_data = None
    with open(filePath, 'rb') as fp:
        image_data = fp.read()
    if not image_data:
        return False
    image_b64 = base64.b64encode(image_data)
    # 上传图片 
    req_url = '{0}/emby/Items/{1}/Images/{2}?api_key={3}'.format(host_name, mediaId, imageType, api_key)
    ret_data = post_html(url=req_url, data=image_b64, retry=1, headers=image_headers)
    if ret_data == '':
        return True
    if ret_data == None:
        return False


def get_premiere_key():
    '''
    获取 Emby Premiere 秘钥 
    '''
    req_url = '{0}/emby/Plugins/SecurityInfo?api_key={1}'.format(host_name, api_key)
    return get_html(req_url)


if __name__=="__main__":
    print(get_premiere_key())
    exit(0)

    root_id = ''
    # 获取指定用户的id 
    for user in get_users():
        if user['name'] == 'root':
            root_id = user['id']
    # 遍历媒体库 
    for item in get_media_library(root_id):
        # 遍历影片 
        for media in get_media_items(item['id'], root_id):
            #####################################
            # 影片详情 
            #####################################
            mediaDetail = get_media_details(media['id'], root_id)
            ## 修改影片信息
            '''
            mediaDetail['LockData'] = True
            mediaDetail['LockedFields'] = ["Name","OriginalTitle","SortName","CommunityRating","CriticRating","Tagline","Overview","OfficialRating","Genres","Studios","Tags"]
            mediaDetail['DateCreated'] = '2021-11-24T07:19:46.0000000Z' # '2022-11-24T07:19:46.0000000Z' 
            set_media_details(media['id'], json.dumps(mediaDetail, ensure_ascii=False)) # 这边不能编码成ascii,服务器不认 
            '''

            #####################################
            # 影片图片 
            #####################################
            for item in get_media_images(media['id']):
                print(item) 
            # 上传新的封面图 
            # set_media_image(media['id'], 'Primary', 'D:\\p2697676764.jpg')
            exit(0)
    