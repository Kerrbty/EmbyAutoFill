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

#####################################################
# 全局数据区 
#####################################################

# 读emby配置 
__base_user_id__ = None
with open(os.path.join(root_dir, 'config', 'config.yaml'), 'r') as config:
    __emby_cfg__ = yaml.safe_load(config)
    __host_name__ = __emby_cfg__['emby']['host']
    __api_key__ = __emby_cfg__['emby']['apikey']
    __base_user_name__ = __emby_cfg__['emby']['user']


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
    req_url = '{0}/Users?api_key={1}'.format(__host_name__, __api_key__)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for jvUser in jvData:
            userInfo = {}
            userInfo['Name'] = jvUser['Name']
            userInfo['Id'] = jvUser['Id']
            userInfo['Admin'] = jvUser['Policy']['IsAdministrator']
            userList.append(userInfo)
    return userList


def __get_userId__():
    global __base_user_id__
    if __base_user_id__:
        return __base_user_id__
    else:
        for user in get_users():
            if user['Name'] == __base_user_name__:
                __base_user_id__ = user['Id']
    return __base_user_id__

def get_media_library():
    """
    获取指定用户的所有媒体库 
    """
    LibraryList = []
    userId = __get_userId__()
    if userId:
        req_url = '{0}/emby/Users/{1}/Items?api_key={2}'.format(__host_name__, userId, __api_key__)
    else:
        req_url = '{0}/emby/Items?api_key={1}'.format(__host_name__, __api_key__)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for jvItem in jvData['Items']:
            # 略过直播 
            if jvItem['Type'] == 'UserView':
                continue
            # 其他媒体库 
            mediaInfo = {}
            mediaInfo['Name'] = jvItem['Name']
            mediaInfo['Id'] = jvItem['Id']
            if 'CollectionType' in jvItem and jvItem['CollectionType'] == 'movies':
                mediaInfo['movie'] = True
            else:
                mediaInfo['movie'] = False
            LibraryList.append(mediaInfo)
    return LibraryList


def get_media_items(libraryId):
    """
    获取媒体库里面所有影片 
    """
    mediaList = []
    nIndex = 0
    userId = __get_userId__()
    while True:
        # 不同参数访问不同的列表 
        if userId:
            req_url = '{0}/emby/Items?ParentId={2}&SortBy=SortName&StartIndex={3}&Limit=50&api_key={4}'.format(__host_name__, userId, libraryId, nIndex, __api_key__)
        else:
            req_url = '{0}/emby/Users/{1}/Items?ParentId={2}&SortBy=SortName&StartIndex={3}&Limit=50&api_key={4}'.format(__host_name__, userId, libraryId, nIndex, __api_key__)
        # 获取到json数据 
        jsonStr = get_html(req_url)
        if not jsonStr:
            break
        jvData = json.loads(jsonStr)
        for item in jvData['Items']:
            mediaInfo = {}
            mediaInfo['Name'] = item['Name']
            mediaInfo['Id'] = item['Id']
            mediaList.append(mediaInfo)
        # 没满50个,说明已经到尾了 
        if jvData['TotalRecordCount'] < 50:
            break
        nIndex += 50
    return mediaList


def get_media_details(mediaId):
    """
    获取影片已经设置的信息  
    """
    mediaDetails = {}
    userId = __get_userId__()
    req_url = '{0}/emby/Users/{1}/Items/{2}?api_key={3}'.format(__host_name__, userId, mediaId, __api_key__)
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
        mediaDetails['LockData'] = jvData['LockData'] if 'LockData' in jvData else False # 锁定此项目以防止被改动 
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
    '''
    设置影片详细信息 
    '''
    req_url = '{0}/emby/Items/{1}?reqformat=json&api_key={2}'.format(__host_name__, mediaId, __api_key__)
    ret_data = post_html(url=req_url, data=jsonStr.encode("utf-8").decode("latin1"), retry=1, headers=json_headers)
    if ret_data == '':
        return True
    if ret_data == None:
        return False


def get_item_images(itemId):
    '''
    获取当前影视/影人已经设置的图片类型列表 
    itemId 为 mediaId 或者 roleId
    '''
    imageList = []
    req_url = '{0}/emby/Items/{1}/Images?api_key={2}'.format(__host_name__, itemId, __api_key__)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        for item in jvData:
            imageList.append(item['ImageType'])
    return imageList


def set_item_image(itemId, imageType, filePath):
    '''
    上传影视/影人图片 
    imageType 取值: Primary(封面图)/ Banner(横幅)/ Logo(标识)/ Thumb(缩略图)/ Disc(光盘)/ Art(艺术图)/Backdrop(背景图) 
    itemId 为 mediaId 或者 roleId
    '''
    if not os.path.exists(filePath):
        return False
    image_data = None
    with open(filePath, 'rb') as fp:
        image_data = fp.read()
    if not image_data:
        return False
    image_b64 = base64.b64encode(image_data)
    # 上传图片 
    req_url = '{0}/emby/Items/{1}/Images/{2}?api_key={3}'.format(__host_name__, itemId, imageType, __api_key__)
    ret_data = post_html(url=req_url, data=image_b64, retry=1, headers=image_headers)
    if ret_data == '':
        return True
    if ret_data == None:
        return False


def get_premiere_key():
    '''
    获取 Emby Premiere 秘钥 
    '''
    req_url = '{0}/emby/Plugins/SecurityInfo?api_key={1}'.format(__host_name__, __api_key__)
    return get_html(req_url)


def get_field_role(roleId):
    '''
    获取 影人 的详细资料 
    '''
    fieldRole = {}
    userId = __get_userId__()
    req_url = '{0}/emby/Users/{1}/Items/{2}?Fields=ChannelMappingInfo&api_key={3}'.format(__host_name__, userId, roleId, __api_key__)
    jsonStr = get_html(req_url)
    if jsonStr:
        jvData = json.loads(jsonStr)
        fieldRole['Id'] = jvData['Id'] if 'Id' in jvData else '' # 
        fieldRole['Name'] = jvData['Name'] if 'Name' in jvData else '' # 标题 
        fieldRole['ChannelNumber'] = ''
        fieldRole['OriginalTitle'] = ''
        fieldRole['ForcedSortName'] = jvData['ForcedSortName'] if 'ForcedSortName' in jvData else '' # 类标题 
        fieldRole['SortName'] = jvData['SortName'] if 'SortName' in jvData else '' # 类标题 
        fieldRole['CommunityRating'] = ''
        fieldRole['CriticRating'] = ''
        fieldRole['IndexNumber'] = None
        fieldRole['ParentIndexNumber'] = None
        fieldRole['SortParentIndexNumber'] = ''
        fieldRole['SortIndexNumber'] = ''
        fieldRole['DisplayOrder'] = ''
        fieldRole['Album'] = ''
        fieldRole['AlbumArtists'] = []
        fieldRole['ArtistItems'] = []
        fieldRole['Overview'] = jvData['Overview'] if 'Overview' in jvData else '' # 描述信息
        fieldRole['Status'] = '' 
        fieldRole['Genres'] = [] 
        fieldRole['Tags'] = []  # 标签 
        fieldRole['TagItems'] = []  # 标签 
        for item in jvData['TagItems']:
            fieldRole['TagItems'].append({'Name': item['Name']})
            fieldRole['Tags'].append(item['Name'])
        fieldRole['Studios'] = [] 
        fieldRole['PremiereDate'] = jvData['PremiereDate'] if 'PremiereDate' in jvData else '' # 出生日期 '1885-12-30T15:55:00.000Z' 
        fieldRole['DateCreated'] = jvData['DateCreated'] if 'DateCreated' in jvData else '' # 加入时间(加入资料库时间) 
        fieldRole['EndDate'] = jvData['EndDate'] if 'EndDate' in jvData else '' # 去世时间 
        fieldRole['ProductionYear'] = ''
        fieldRole['Video3DFormat'] = ''
        fieldRole['OfficialRating'] = ''
        fieldRole['CustomRating'] = '' 
        fieldRole['LockData'] = jvData['LockData'] if 'LockData' in jvData else False # 锁定此项目以防止被修改 
        fieldRole['LockedFields'] = jvData['LockedFields'] if 'LockedFields' in jvData else ["Name", "SortName", "Overview", "Tags"] # 锁定项目列表 
        fieldRole['ProviderIds'] = jvData['ProviderIds'] if 'ProviderIds' in jvData else {'Imdb':'','Tmdb':'','Tvdb':''} # 外部ids(Imdb / Tmdb / Tvdb) 
        fieldRole['PreferredMetadataLanguage'] = jvData['PreferredMetadataLanguage'] if 'PreferredMetadataLanguage' in jvData else 'zh-CN' # 首选元数据下载语言 
        fieldRole['PreferredMetadataCountryCode'] = jvData['PreferredMetadataCountryCode'] if 'PreferredMetadataCountryCode' in jvData else 'CN' # 国家 
        fieldRole['ProductionLocations'] = jvData['ProductionLocations'] if 'ProductionLocations' in jvData else [] # 出生地 
        fieldRole['Taglines'] = []
    return fieldRole


def set_field_role(roleId, jsonStr):
    '''
    设置影人详细信息 
    '''
    req_url = '{0}/emby/Items/{1}?reqformat=json&api_key={2}'.format(__host_name__, roleId, __api_key__)
    ret_data = post_html(url=req_url, data=jsonStr.encode("utf-8").decode("latin1"), retry=1, headers=json_headers)
    if ret_data == '':
        return True
    if ret_data == None:
        return False


if __name__=="__main__":
    root_id = __get_userId__()
    logger(__base_user_name__,'用户的id为:', root_id)

    # 影人数据 
    fieldRole = get_field_role(904)
    if fieldRole:
        logger('获取影人', fieldRole['Name'], '(904)的资料:', fieldRole)
        fieldRole['Overview'] = '新的描述信息'
        '''
        if set_field_role(904, json.dumps(fieldRole, ensure_ascii=False)):
            logger('已修改该影人描述为"新的描述信息"')
        '''

    # 遍历媒体库 
    logger("测试遍历媒体库")
    for item in get_media_library():
        # 遍历影片 
        logger("当前媒体库为:", item['Name'])
        for media in get_media_items(item['Id']):
            #####################################
            # 影片详情 
            #####################################
            logger(item['Name'], '媒体库中的媒体', media['Name'])
            mediaDetail = get_media_details(media['Id'])
            logger('获取到资料为', mediaDetail)
            ## 修改影片信息
            mediaDetail['LockData'] = False
            mediaDetail['LockedFields'] = ["Name","OriginalTitle","SortName","CommunityRating","CriticRating","Tagline","Overview","OfficialRating","Genres","Studios","Tags"]
            mediaDetail['DateCreated'] = '2021-11-24T07:19:46.0000000Z' # '2022-11-24T07:19:46.0000000Z' 
            logger('修改媒体创建时间')
            '''
            if set_media_details(media['Id'], json.dumps(mediaDetail, ensure_ascii=False)): # 这边不能编码成ascii,服务器不认 
                logger('修改媒体创建时间并解锁媒体项目成功')
            '''

            #####################################
            # 影片图片 
            #####################################
            logger('该影片当前包含图片:', )
            for item in get_item_images(media['Id']):
                print(item + ',', end='') 
            print('')
            # 上传新的封面图 
            '''
            set_item_image(media['Id'], 'Primary', 'D:\\p2697676764.jpg') 
            '''
            exit(0)
