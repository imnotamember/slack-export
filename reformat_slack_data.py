import datetime
import io
import json
import os
from os.path import join as pj
import file_info
import aiohttp
import discord
from PIL import Image
import errors
from pdfrw import PdfReader
import giphy_client
from giphy_client.rest import ApiException
from pprint import pprint
from settings import EMBED_COLORS

fmt = "%Y-%m-%d %H:%M:%S"
GIPHY_API = giphy_client.DefaultApi()
GIPHY_TOKEN = "wgpYcwq401GK7ygUDkaIUkOXEmTti8Dr"
GIPHY_BOT = "B2TGYDACQ"

DEFAULT_MESSAGE = 'N/A'

USER_MAP = {
        "Fun Guy"            : "imnotamember",
        "Old"                : "OldCanada",
        "zoezoeyyyy"         : "zoezoeyyyy",
        "k"                  : "k",
        "Joshua da Scientist": "hellojoshua",
        "Justin Frandsen"    : "Froxlines",
        "lizzy"              : "lizzy",
        "Logan M"            : "Logan M",
        "Payton"             : "Payton",
        "SeaPancake"         : "SeagoingPancake"}
# USER_MAP = {
#         "imnotamember": "Fun Guy",
#         "OldCanada": "Old",
#         "zoezoeyyyy": "zoezoeyyyy",
#         "k": "k",
#         "hellojoshua": "Joshua da Scientist",
#         "Froxlines": "Justin Frandsen",
#         "lizzy": "lizzy",
#         "Logan M": "Logan M",
#         "Payton": "Payton"}

ACCESS_TOKEN = 'xoxe-78060924404-752010636628-739702343410-211ee24aab9c44f3dfd9dbc1a65cbf01'

MESSAGE_FORMATTING = dict(channel_join="{slack_handle}{post_slack_handle_text}",
                          channel_purpose="{set_purpose} Updated Settings\nPurpose:\n{purpose}",
                          )
STATIC_IMAGE = "STATIC"
DYNAMIC_IMAGE = 'DYNAMIC'
GIPHY_IMAGE = 'GIPHY'
IMAGE_TYPES = {
        'STATIC' : STATIC_IMAGE,
        'JPG'    : STATIC_IMAGE,
        'JPEG'   : STATIC_IMAGE,
        'PNG'    : STATIC_IMAGE,
        'SVG'    : STATIC_IMAGE,
        'DYNAMIC': DYNAMIC_IMAGE,
        'GIF'    : DYNAMIC_IMAGE,
        'GIPHY'  : DYNAMIC_IMAGE}

users = None

base_path = os.path.expanduser('~')
slack_backup_path = pj('Box', 'Slack_backup')

slack_documents_path = pj(slack_backup_path, 'Documents')
slack_files_path = pj(slack_backup_path, 'Files')
slack_images_path = pj(slack_backup_path, 'Images')
slack_videos_path = pj(slack_backup_path, 'Videos')

slack_pdf_path = pj(slack_documents_path, 'PDF')
slack_other_documents_path = pj(slack_documents_path, 'Other')

slack_binary_path = pj(slack_files_path, 'Binary')
slack_text_path = pj(slack_files_path, 'Text')

slack_dynamic_images_path = pj(slack_images_path, DYNAMIC_IMAGE)
slack_static_images_path = pj(slack_images_path, STATIC_IMAGE)


def generate_user_info(slack_backup_path, user_info=None):
    if user_info is None:
        user_info = (
                ('name', "real_name"),
                ('discord_handle', "display_name"),
                ('avatar', "image_original"),
                ('email', "email"),
                ('status', "status_text"),
                ('status_emoji', "status_emoji"),
                ('title', "title"),
                ('id', "id"))
    slack_users = {}
    users_path = pj(slack_backup_path, 'users.json')
    with open(users_path) as users_file:
        users = json.load(users_file)
        for user in users:
            # if user['id'] == 'U782BTYDS':
            #     print('found him')
            formatted_user = dict(url=discord.Embed.Empty)
            profile = user["profile"]
            for (info_discord, info_slack) in user_info:
                # print(info_discord, info_slack, "\n{0} == 'discord_handle' is {1}".format(info_discord, info_discord == 'discord_handle'))
                if info_discord == 'discord_handle':
                    formatted_user["slack_handle"] = "{0} ({1})".format(profile['real_name'], profile[info_slack])
                    try:
                        formatted_user[info_discord] = USER_MAP[profile[info_slack]]
                    except KeyError:
                        formatted_user[info_discord] = profile[info_slack]
                elif info_discord == "id":
                    slack_id = user[info_slack]
                else:
                    try:
                        formatted_user[info_discord] = profile[info_slack]
                    except KeyError:
                        formatted_user[info_discord] = ""
            # try:
            slack_users[slack_id] = formatted_user
            # except KeyError:
            #     return
    return slack_users


def collect_slack_channel_messages(slack_channel_path):
    slack_channel_messages = os.listdir(slack_channel_path)
    slack_messages = []
    for _file in slack_channel_messages:
        if '.json' in os.path.splitext(_file):
            slack_messages.append(pj(slack_channel_path, _file))
    return sorted(slack_messages)


def get_user_info(guild, slack_users):
    for slack_id, user in slack_users.items():
        try:
            member = guild.get_member_named(user['discord_handle'])
            assert member is not None
            user["id"] = member.id
        except KeyError:
            user["id"] = None
        except AttributeError:
            user["id"] = None
        except AssertionError:
            user["id"] = None
    return slack_users


async def image_prep(image_info, user_info, text, timestamp, image_type=STATIC_IMAGE, image_save=True, inline=True):
    EMPTY_EMBED = discord.Embed.Empty
    extra_parameters = {}
    post_info = dict(timestamp=timestamp, text=text)
    # pprint(image_info)

    if image_type == GIPHY_IMAGE:
        # post_info['name'] = image_info['title_link'].split('/')[-1] + ".gif"
        post_info['name'] = image_info['title'].replace('_', '-').replace(' ', '-') + ".gif"
        post_info['id'] = image_info["title_link"].split('-')[-1]
        post_info['link'] = image_info['image_url'].strip('\\')
        post_info['footer'] = image_info['footer']
        post_info['text'] = "Giphy search term(s): {0}\n".format(image_info['title'])
    elif image_type != GIPHY_IMAGE:
        post_info['name'] = image_info['name'].replace('_', '-')
        post_info['link'] = image_info['url_private']
        post_info['footer'] = "User-posted image"
    else:
        return EMPTY_EMBED
    image_path = pj(slack_images_path, image_type, post_info['name'])
    image_save_path = pj(base_path, image_path)
    post_info['text'] += "File stored at: {0}".format(image_path)
    image_type = IMAGE_TYPES[image_type]

    # embed_dict = {}
    # for label in ('title', 'footer'):
    #     info = post_info[label]
    #     if info is not None:
    #         embed_dict[label] = info
    #         text += "{0}\n".format(info)
    # embed = discord.Embed(**embed_dict) \

    # # Timestamp converted via:
    # datetime.datetime.fromtimestamp(int("1284105682")).strftime('%H:%M:%S')
    """
    embed = discord.Embed(**post_info) \
        .set_author(name=user_info['slack_handle'], url=user_info['url'], icon_url=user_info['avatar']) \
        .set_footer(text=post_info['footer'])
    """
    image = await get_posted_image(post_info['name'], image_save_path, post_info['link'],
                                   image_save=image_save, image_type=image_type)
    if image is None:
        return EMPTY_EMBED
    elif type(image) is discord.File:
        return {"file": image}
    elif type(image) is bool:
        if image:
            extra_parameters['file'] = discord.File(image_save_path, filename=post_info['name'])
            image_url = "attachment://{0}".format(post_info['name'])
        else:
            # image_link = get_giphy(GIPHY_TOKEN, post_info['id'])
            # image_url = '<img src="{0}">'.format(image_link)  # post_info['link'])
            image_url = get_giphy(GIPHY_TOKEN, post_info['id'])
            image_url = post_info['link']
            # embed.title = image_save_path
        """
        embed.set_image(url=image_url)
        # pprint(embed.fields)
        embed\
            .insert_field_at(index=0, name="Time:", value=timestamp.strftime('%I:%M:%S %p'), inline=inline)\
            .insert_field_at(index=1, name="File stored at:", value=image_save_path, inline=inline)
        """
    d = dict(url=image_url, colour=discord.Colour.dark_teal().value, timestamp=timestamp,
             footer=dict(text=post_info['footer']), image=dict(url=image_url),
             author=dict(name=user_info['slack_handle'],  # url=user_info['url'],
                         icon_url=user_info['avatar']),
             fields=[dict(name="File stored at: ", value=image_save_path, inline=inline)])
    embed = discord.Embed.from_dict(d)
    # if text != '':
    #     embed.add_field(name="Message", value=text, inline=inline)
    # else:
    #     embed.add_field(name="Message", value=DEFAULT_MESSAGE, inline=inline)
    pprint(d)
    extra_parameters['embed'] = embed
    return extra_parameters


async def file_prep(file_info, slack_channel, user_info, text, timestamp, inline=True, file_save=True):
    empty_embed = discord.Embed.Empty
    extra_parameters = {}
    post_info = {
            'name'       : file_info['name'].replace('_', '-'),
            'title'      : file_info['name'],
            'description': None,
            'footer'     : "Auto-generated by Slack-To-Discord: https://imnotamember.github.io/slack-to-discord",
            'url'        : None,
            'colour'     : discord.Colour.from_rgb(0, 137, 123)}
    # post_info['url'] = file_info['url_private']

    # default_sub_embed = dict(name=None, value=None, url=None, icon_url=None, inline=True)
    embed = {
            'image' : {},  # default_sub_embed.copy(),
            'author': {},  # default_sub_embed.copy(),
            'field' : {}}  # default_sub_embed.copy()}

    file_save_path = pj(slack_channel, post_info['name'])
    file_attachment = await get_posted_file(post_info['name'],
                                            file_save_path,
                                            file_info['url_private'],
                                            file_save=file_save)
    if file_attachment is None:
        return empty_embed
    elif type(file_attachment) is discord.File:
        return {"file": file_attachment}
    elif file_attachment == post_info['url']:
        post_info['description'] = "Link to file (Size greater than Discord limit of 8 MB)"
        post_info['url'] = file_attachment
    else:
        embed['image']['url'] = "attachment://{0}".format(post_info['name'])
        extra_parameters['file'] = discord.File(file_attachment, filename=post_info['name'])

    if os.path.split(file_attachment)[1] != post_info['name']:
        post_info['name'] = os.path.split(file_attachment)[1]

    embed['author']['name'] = user_info['slack_handle']
    embed['author']['url'] = user_info['url']
    embed['author']['icon_url'] = user_info['avatar']
    embed['field']['name'] = 'Time'
    embed['field']['value'] = timestamp
    embed['field']['inline'] = inline
    # for label in ('title', 'description', 'url', 'footer'):
    #     info = post_info[label]
    #     if info is not None:
    #         embed['main'][label] = info
    #         text += "{0}\n".format(info)

    # embed_object = discord.Embed(**post_info)
    # .set_image(url=attachment_url)\
    # .set_author(name=user_info['slack_handle'], url=user_info['url'], icon_url=user_info['avatar']) \
    # .add_field(name="Time", value=timestamp, inline=False)
    embed_object = discord.Embed(**post_info).set_author(**embed['author']).add_field(**embed['field'])
    if embed['image'] != {}:
        embed_object.set_image(**embed['image'])
    if text != '':
        embed_object.add_field(name="Message", value=text, inline=inline)
    else:
        embed_object.add_field(name="Message", value=DEFAULT_MESSAGE, inline=inline)
    extra_parameters['embed'] = embed_object
    return extra_parameters


async def get_posted_image(image_name, file_path, url, image_save=True, image_type='static'):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as result:
            if result.status != 200:
                # return await channel.send(errors.DOWNLOAD_FAILED)
                print(errors.DOWNLOAD_FAILED)
                # data = io.BytesIO(await result.read())
                # return discord.File(data, image_name)
                print('Download failed')
                return None
            elif result.status == 200:
                if image_save:
                    image = await result.content.read()
                    await convert_image_to_file(file_path, image)
                elif not image_save:
                    return url  # embed image dynamically with link
                if image_type == DYNAMIC_IMAGE:
                    return False
                else:
                    return True  # True == Success
    data = io.BytesIO(await result.read())
    return discord.File(data, image_name)


async def convert_image_to_file(file_path, image_data):
    image_stream = io.BytesIO(image_data)
    Image.open(image_stream).save(file_path)


async def convert_attachment_to_file(file_name, file_path, attachment):
    with open(file_path, 'wb') as fd:
        async for data in attachment.content.iter_chunked(1024):
            fd.write(data)
    # # TODO: Create a pdf-sorting module for academic articles so article's get posted with
    # #  author's/journal name/pub date/Title/keywords.
    # #  Also utilize new module for article scraping/aggregating.
    # if file_name[-3:] == 'pdf':
    #     file_path = renameFileToPDFTitle(os.path.split(file_path)[0], file_name)
    file_size, file_size_magnitude, file_info_string = file_info.file_size(file_path)
    print(file_info_string)
    if file_size >= 8.0 and file_size_magnitude == 'MB':
        return None
    else:
        return file_path


async def get_posted_file(file_name, file_path, url, file_save=True):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as result:
            if file_save:
                # print("File Size: ", result.content._size)
                if result.status == 200:
                    file_path = await convert_attachment_to_file(file_name, file_path, result)
                    if file_path is None:
                        return url
                    else:
                        return file_path
                else:
                    print('Download failed')
                    return None
            else:
                if result.status != 200:
                    print(errors.DOWNLOAD_FAILED)
                data = io.BytesIO(await result.read())
                return discord.File(data, file_name)


def renameFileToPDFTitle(path, fileName):
    fullName = os.path.join(path, fileName)
    # Extract pdf title from pdf file
    newName = PdfReader(fullName).Info.Title
    # Remove surrounding brackets that some pdf titles have
    newName = newName.strip('()') + '.pdf'
    if newName in ('', 'pdf', '.pdf'):
        return fullName
    newFullName = os.path.join(path, newName)
    os.rename(fullName, newFullName)
    return newFullName


def slack_id_to_handle(id, users):
    return users[id]['slack_handle']


def replace_tags(message, users):
    for user_id, user_info in users.items():
        mention = "<@{0}>".format(user_id)
        if mention in message:
            message = message.replace(mention, "@{0}".format(user_info['slack_handle']))
    return message


async def process_message(raw_message, discord_users, slack_channel):
    """

    :rtype: dict
    :param raw_message: Raw message data (in parsed JSON format; typically a dictionary)
    :param discord_users: Collection of Discord users to match to Slack message.
    :param slack_channel: Name of the Slack Channel the message originates from.
    :return: Processed message ready to send as a Discord embed.
    """
    processed_message = {}
    message_type, slack_user_id, user_info, timestamp, text, bot_id, files, attachments, kwargs = \
        await extract_message_info(discord_users, **raw_message)
    # if message_type is not None and attachments is not None:
    if message_type is not None and attachments is not None:
        text = replace_tags(text, users)
        # Handle bots
        if bot_id is not None:
            if bot_id == GIPHY_BOT:
                giphy_attachment = attachments[0]
                processed_message = \
                    await image_prep(giphy_attachment, user_info, text, timestamp, image_type='GIPHY')
        # Handle file attachments (images, gif's, pdf's, etcl)
        elif files is not None:
            for file_attachment in files:
                if 'image' in file_attachment['mimetype']:
                    image_type = IMAGE_TYPES[file_attachment['mimetype'].split('/')[1].upper()]
                    processed_message = \
                        await image_prep(file_attachment, user_info, text, timestamp, image_type=image_type)
                elif 'application' in file_attachment['mimetype']:
                    processed_message = await file_prep(file_attachment, slack_channel, user_info, text, timestamp)
        else:
            embed = discord.Embed(timestamp=timestamp) \
                .set_author(name=user_info['slack_handle'], url=user_info['url'], icon_url=user_info['avatar']) \
                .add_field(name="Time", value=timestamp, inline=False)
            if text != '':
                embed.add_field(name="Message", value=text, inline=False)
            else:
                embed.add_field(name='Message', value=DEFAULT_MESSAGE, inline=False)
            processed_message = {'embed': embed}
    # print(processed_message, processed_message == {})
    return processed_message


async def extract_message_info(discord_users, type=None, user=None, ts=None, text=None, bot_id=None, files=None,
                               attachments=None, **kwargs):
    # Convert timestamp to `datetime` iso string
    timestamp = datetime.datetime.fromtimestamp(float(ts)).isoformat()
    user_info = discord_users[user]
    # Handle bots
    if bot_id is not None:
        if bot_id == GIPHY_BOT:
            pass  # TODO: set up to handle all types
    if 'subtype' in kwargs:
        type = kwargs['subtype']
        # if 'channel_join' == subtype:  # "has joined" in text:
        #     text = user_info['slack_handle'] + text.split('>')[1]
        text_search = dict(
                slack_handle=(user_info['slack_handle'], None),
                post_slack_handle_text=('>', 1),
                set_purpose=('set the channel purpose', 0),
                purpose=('set the channel purpose: ', 1),
                text=(text, None))
        for term, (phrase, split_index) in text_search.items():
            if split_index is not None:
                try:
                    text_search[term] = text.split(phrase)[split_index]
                except IndexError:
                    text_search[term] = ''
            else:
                text_search[term] = phrase
        text = MESSAGE_FORMATTING[type].format(slack_handle=text_search['slack_handle'],
                                                  post_slack_handle_text=text_search['post_slack_handle_text'],
                                                  set_purpose=text_search['set_purpose'],
                                                  purpose=text_search['purpose'],
                                                  text=text_search['text'])
    return type, user, user_info, timestamp, text, bot_id, files, attachments, kwargs


async def message_prep(embed_info, file_info=None, type='DEFAULT'):
    file = file_info
    if file_info is not None:
        file = discord.File(**file_info)
    embed = discord.Embed.from_dict(dict(color=EMBED_COLORS[type], **message))
    message = dict(embed=embed, file=file)
    return message


def get_giphy(token, gif_id):
    try:
        # Search Endpoint
        api_response = GIPHY_API.gifs_gif_id_get(token, gif_id)
        # pprint(api_response)
        return api_response.data.images.original.url
    except ApiException as e:
        print("Exception when calling DefaultApi->gifs_gif_id_get_with_http_info: %s\n" % e)
