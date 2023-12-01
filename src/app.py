#!/usr/bin/python
# -*- coding: UTF-8 -*- 

import os,sys
import json

cur_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cur_dir)

from module.comm import logger
from module.emby import get_media_library, get_media_items  # 按级遍历 
from module.emby import get_media_details, set_media_details  # 影片信息 
from module.emby import get_field_role, set_field_role # 影人信息 
from module.emby import get_item_images, set_item_image, set_item_image_raw # 项目图片 
from module.douban import update_media_with_douban, update_role_with_douban # 豆瓣抓取数更新 

def enum_all_media():
    for item in get_media_library():
        for media in get_media_items(item['Id']):
            yield media


def enum_media_role(mediaId):
    mediaDetail = get_media_details(mediaId)
    for role in mediaDetail['People']:
        yield role


def update_media_info(mediaId, forceUpdate = False):
    mediaDetail = get_media_details(mediaId)
    if not forceUpdate and mediaDetail['LockData']:
        # 项目已被锁,且不强制更新的情况 
        return 1
    imageList = get_item_images(mediaId)
    if update_media_with_douban(mediaDetail, imageList, set_item_image_raw, forceUpdate):
        if set_media_details(mediaId, json.dumps(mediaDetail, ensure_ascii=False)):
            return 0
        else:
            return -2
    else:
        return -1


def update_role_info(roleId, forceUpdate = False):
    fieldRole = get_field_role(roleId)
    if not forceUpdate and fieldRole['LockData']:
        # 项目已被锁,且不强制更新的情况 
        return 1
    imageList = get_item_images(roleId)
    if update_role_with_douban(fieldRole, imageList, set_item_image_raw, forceUpdate):
        if set_field_role(roleId, json.dumps(fieldRole, ensure_ascii=False)):
            return 0
        else:
            return -2
    else:
        return -1


def update_all():
    for media in enum_all_media():
        logger('正在更新影片:', media['Name'], ', Id:', media['Id'], 'Type:', media["Type"])
        update_media_info(media['Id'], True)
        logger('开始遍历更新该影片的演员列表...')
        for role in enum_media_role(media['Id']):
            logger('正在更新影人:', role['Name'], ', Id:', role['Id'], 'Type:', role["Type"])
            update_role_info(role['Id'])


if __name__=="__main__":
    update_all()
