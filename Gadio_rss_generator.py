import os
import time
import json
import random
import datetime
import requests

GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
NOW_GMT = lambda: datetime.datetime.utcnow().strftime(GMT_FORMAT)

RSS_TEMPLATE_HEADER = '''
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:sy="http://purl.org/rss/1.0/modules/syndication/" xmlns:slash="http://purl.org/rss/1.0/modules/slash/" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:media="http://search.yahoo.com/mrss/" xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0" version="2.0">
    <channel>
        <title><![CDATA[ Gadio ]]></title>
        <link>机核网电台 https://www.gcores.com/radios</link>
        <atom:link href="https://rsshub.app/xiaoyuzhou/podcast/5e280fb0418a84a0461fc251" rel="self" type="application/rss+xml"/>
        <description>
            <![CDATA[ 机核网出品的Gadio是中国首档游戏专门播客，将一切与游戏有关的事情分享给热爱游戏的你！ 欢迎访问官方网站 www.gcores.com/radios ]]>
        </description>
        <generator>http://github.com/haolloyin/Gadio_rss_generater</generator>
        <webMaster>http://github.com/haolloyin/Gadio_rss_generater</webMaster>
        <itunes:author>机核网电台 www.gcores.com/radios</itunes:author>
        <itunes:explicit>clean</itunes:explicit>
        <language>zh-cn</language>
        <image>
            <url> https://static.gcores.com/assets/6909fc2fc5fa1394cedce575dd49de33.png </url>
            <title> <![CDATA[ Gadio ]]> </title>
            <link> https://www.gcores.com/radios </link>
        </image>
        <lastBuildDate> {lastBuildDate} </lastBuildDate>
        <ttl>120</ttl>
'''

RSS_TEMPLATE_FOOTER = '''
    </channel>
</rss>
'''

ITEM_TEMPLATE = '''
<item>
    <title>{radio_title}</title>
    <link>{radio_url}</link>
    <guid>{radio_mp3_url}</guid>
    <pubDate>{radio_pubDate}</pubDate>
    <itunes:image href="{radio_image_url}"/>
    <enclosure url="{radio_mp3_url}" type="audio/mpeg"/>
    <itunes:duration>{radio_duration}</itunes:duration>

    <content:encoded>
    <![CDATA[
{radio_desc}

{radio_content}
    ]]>
    </content:encoded>
</item>
'''

HISTORY_RADIO_FILE      = 'Gadio_history.xml'
NEW_RADIO_FILE          = 'Gadio_new.xml'
GADIO_RSS_FILE          = 'Gadio.xml'
GADIO_CONF_FILE         = 'Gadio_conf.json'
NEWEST_RADIO_ID         = 0 # 当前最新的 id
SAVED_RADIO_ID          = 0 # 已保存的最新 id


def _http(url, headers=None, log=True):
    if log:
        print(f'Fetching: {url}')
    r = requests.get(url)
    return r.json()


def get_radio_detail(radio_id):
    url = f'https://www.gcores.com/gapi/v1/radios/{radio_id}?include=category,user,media,djs,media.timelines'
    return _http(url)


def get_included_name(included_arr, id_type):
    id_   = id_type['id']
    type_ = id_type['type']
    for i in included_arr:
        if i['type'] == 'categories' and i['id'] == id_:
            return i['attributes']['name']
        elif i['type'] == 'users' and i['id'] == id_:
            return i['attributes']['nickname']
    return ''


def main():
    # 每次获取 100 期
    offset = 0
    limit = 3
    url = f'https://www.gcores.com/gapi/v1/radios?page[limit]={limit}&page[offset]={offset}&sort=-published-at&include=category,user,djs&filter[list-all]=0&fields[radios]=title,desc,excerpt,is-published,thumb,app-cover,cover,comments-count,likes-count,bookmarks-count,is-verified,published-at,option-is-official,option-is-focus-showcase,duration,draft,audit-draft,user,comments,category,tags,entries,entities,similarities,latest-collection,collections,operational-events,portfolios,catalog-tags,media,djs,latest-album,albums,is-free'

    resp_dic = {}
    try:
        resp_dic = _http(url, log=False)
    except Exception as ex:
        print(f'error json.loads(): {ex}')
        return

    data     = resp_dic.get('data', [])
    included = resp_dic.get('included', {})
    if len(data) == 0:
        return '已经到底'

    item_list            = [] # 不区分类目
    categories_item_list = {} # 按类目

    global SAVED_RADIO_ID, NEWEST_RADIO_ID
    NEWEST_RADIO_ID = data[0]['id']

    for idx, d in enumerate(data):
        radio_id = d['id']
        if radio_id == SAVED_RADIO_ID:
            # 遇到上一次的最新 id，跳出
            SAVED_RADIO_ID = NEWEST_RADIO_ID
            break

        #time.sleep(random.randint(30,300)) # 休眠 30~300s

        attributes    = d.get('attributes', {})
        relationships = d.get('relationships', {})
        title         = attributes.get('title', '')
        desc          = attributes.get('desc', '')
        excerpt       = attributes.get('excerpt', '')
        cover         = attributes.get('cover', '')
        radio_url     = f'/radios/{radio_id}'
        category      = get_included_name(included, relationships['category']['data'])

        if title.startswith('[会员专享]') or category == '会员专享':
            print(f'----> 跳过 {title}\n')
            continue

        anchors       = relationships['djs']['data']
        anchor_cnt    = len(anchors)
        anchors_str   = ', '.join([get_included_name(included, u) for u in anchors])
        duration      = attributes.get('duration', 0)
        like_cnt      = attributes.get('likes-count', 0)
        comment_cnt   = attributes.get('comments-count', 0)
        release_time  = attributes.get('published-at', '')[:10] # 2023-07-06T23:00:00.000+08:00

        # 通过 API 获取单集的信息
        dic            = get_radio_detail(radio_id)
        published_time = dic['data']['attributes']['published-at'].strip() # 2022-09-11T23:00:00.000+08:00
        published_time = datetime.datetime.fromisoformat(published_time).strftime(GMT_FORMAT) # 'Sun, 11 Sep 2022 23:00:00 GMT'
        media_id       = dic['data']['relationships']['media']['data']['id']
        arr            = json.loads(dic['data']['attributes']['content'])['blocks']
        desc_arr       = []
        for i in arr:
            s = i['text'].strip()
            if s != '':
                desc_arr.append(s)
        radio_desc     = '<p>' + '</p>\n<p>'.join(desc_arr) + '</p>\n'
        mp3_url        = ''
        radio_duration = ''
        timeline_ids   = []
        timelines      = []

        for kv in dic['included']:
            id = kv['id']
            if id == media_id:
                mp3_url      = kv['attributes']['audio'].strip()
                timeline_ids = [item['id'] for item in kv['relationships']['timelines']['data']]
                h            = int(int(duration) / 3600)
                seconds      = int(duration) - 3600 * h
                m            = int(seconds / 60)
                s            = seconds - 60 * m
                if h > 0: radio_duration = '{}:{:0>2}:{:0>2}'.format(h, m, s)
                else:     radio_duration = '{}:{:0>2}'.format(m, s)

            elif id in timeline_ids:
                at         = int(kv['attributes']['at'])
                hour       = int(at / 3600)
                minute     = int((at - hour * 3600) / 60)
                second     = int(at % 60)
                at_time    = '{:0>2}:{:0>2}:{:0>2}'.format(hour, minute, second)
                at_title   = kv['attributes']['title'].strip()
                at_content = kv['attributes']['content'].strip().replace(' ','').replace('\n','')
                at_href    = kv['attributes']['quote-href'].strip()
                timelines.append((at, at_time, at_title, excerpt, at_content, at_href))

        timelines.sort(key=lambda item: item[0])
        radio_timelines = '<h4>---- 时间轴 ----</h4>\n<ul>\n'
        for item in timelines:
            radio_timelines += f'<li>{item[1]} {item[2]}</li></br>\n'
            radio_timelines += f'{item[4]}</br>\n'
            radio_timelines += f'<a href="{item[5]}">link</a></br></br>\n' if len(item[5])>0 else ''
        radio_timelines += '</ul>'

        radio_content  = f'<p>主播：{anchors_str}</p>\n'
        radio_content += f'<p>点赞：{like_cnt}，评论：{comment_cnt}，分类：{category}</p>\n'
        radio_content += radio_timelines

        print(f'title: {title}\nradio_url: {radio_url}\n'
              f'分类: {category}\n参与人数: {anchor_cnt}, {anchors_str}\n'
              f'发布时间: {release_time}\n时长: {duration}秒，{radio_duration}\n'
              f'点赞: {like_cnt}\n评论: {comment_cnt}\n')

        radio_item = ITEM_TEMPLATE.format(
                radio_title=f'[{category}]{title}',
                radio_desc=radio_desc.strip(),
                radio_content=radio_content,
                radio_pubDate=published_time,
                radio_url=f'https://www.gcores.com{radio_url}',
                radio_image_url=f'https://image.gcores.com/{cover}',
                radio_mp3_url=f'https://alioss.gcores.com/uploads/audio/{mp3_url}',
                radio_duration=radio_duration)

        # 写入新节目
        with open(NEW_RADIO_FILE, 'a+') as f:
            f.write(radio_item)
            f.write('\n\n')

    history_content = ''
    with open(HISTORY_RADIO_FILE,'r') as f:
        history_content = f.read()

    new_content = ''
    with open(NEW_RADIO_FILE,'r') as f:
        new_content = f.read()

    # 更新历史文件，相当于追加新内容
    with open(HISTORY_RADIO_FILE,'w') as f:
        f.write(new_content)
        f.write(history_content)

    # 更新完整的 rss 文件
    with open(GADIO_RSS_FILE,'w') as f:
        f.write(RSS_TEMPLATE_HEADER)
        f.write(new_content)
        f.write(history_content)
        f.write(RSS_TEMPLATE_FOOTER)


def init_files():
    if not os.path.exists(HISTORY_RADIO_FILE):
        with open(HISTORY_RADIO_FILE,'w') as f:
            f.write('')

    if not os.path.exists(NEW_RADIO_FILE):
        with open(NEW_RADIO_FILE,'w') as f:
            f.write('')

    if not os.path.exists(GADIO_RSS_FILE):
        with open(GADIO_RSS_FILE,'w') as f:
            f.write('')

    backup_history = ''
    with open(NEW_RADIO_FILE,'r') as f:
        backup_history = f.read()

    with open('backup_'+NEW_RADIO_FILE,'w') as f:
        f.write(backup_history)

    with open(NEW_RADIO_FILE,'w') as f:
        f.write('')



if __name__ == '__main__':
    # 参考= https://rsshub.app/xiaoyuzhou/podcast/5e280fb0418a84a0461fc251
    # 参考= https://anobody.im/podcast/rss.xml
    # 订阅= https://gist.githubusercontent.com/haolloyin/acbfde78b3f913b8be2ac30e052750ec/raw/923895e2aaa23ce794c93632deaef641a7b3ec00/Gadio.xml
    # xml = https://gist.github.com/haolloyin/acbfde78b3f913b8be2ac30e052750ec
    # 脚本= https://gist.github.com/haolloyin/56dad9affab952e06a6b8aae86332b6e
    # API = https://www.gcores.com/gapi/v1/radios/156121?include=category,user,media,djs,media.timelines

    init_files()
    main()
