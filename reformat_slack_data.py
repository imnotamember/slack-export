import io
import json
import os
from os.path import join as pj

import aiohttp
import discord
from PIL import Image
import errors
from pdfrw import PdfReader

DEFAULT_MESSAGE = 'N/A'

USER_INFO = {
        'name'        : "real_name",
        'handle'      : "display_name",
        'avatar'      : "image_original",
        'email'       : "email",
        'status'      : "status_text",
        'status_emoji': "status_emoji",
        'title'       : "title",
        'id'          : "id"}

# USER_MAP = dict(imnotamember="Josh Zosky")
USER_MAP = {"Fun Guy": "imnotamember"}

ACCESS_TOKEN = 'xoxe-78060924404-752010636628-739702343410-211ee24aab9c44f3dfd9dbc1a65cbf01'


def generate_user_info(slack_backup_path):
    slack_users = {}
    users_path = pj(slack_backup_path, 'users.json')
    with open(users_path) as users_file:
        users = json.load(users_file)
        for user in users:
            formatted_user = dict(url=discord.Embed.Empty)
            profile = user["profile"]
            for info_discord, info_slack in USER_INFO.items():
                if info_discord == "handle":
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
            try:
                slack_users[slack_id] = formatted_user
            except KeyError:
                return
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
            member = guild.get_member_named(USER_MAP[slack_id])
            user["id"] = member.id
        except KeyError or AttributeError:
            user["id"] = None
    return slack_users


async def image_prep(image_info, slack_channel, user_info, text, timestamp, image_type='file', image_save=True):
    EMPTY_EMBED = discord.Embed.Empty
    post_info = {}
    if image_type == "file":
        post_info['name'] = image_info['name'].replace('_', '-')
        post_info['link'] = image_info['url_private']
        post_info['title'] = None
        post_info['footer'] = None
    elif image_type == 'gif':
        post_info['name'] = image_info['title_link'].split('/')[-1] + ".gif"
        post_info['link'] = image_info['image_url']
        post_info['title'] = image_info['title']
        post_info['footer'] = image_info['footer']
    else:
        return EMPTY_EMBED
    image_save_path = pj(slack_channel, post_info['name'])
    image = await get_posted_image(post_info['name'], image_save_path, post_info['link'], image_save=image_save)
    if image is None:
        return EMPTY_EMBED
    elif type(image) is discord.File:
        return {"file": image}
    extra_parameters = {}
    attachment_url = "attachment://{0}".format(post_info['name'])
    extra_parameters['file'] = discord.File(image_save_path, filename=post_info['name'])
    embed_dict = {}
    for label in ('title', 'footer'):
        info = post_info[label]
        if info is not None:
            embed_dict[label] = info
            text += "{0}\n".format(info)
    embed = discord.Embed(**embed_dict) \
        .set_image(url=attachment_url) \
        .set_author(name=user_info['handle'],
                    url=user_info['url'],
                    icon_url=user_info['avatar']) \
        .add_field(name="Time", value=timestamp, inline=False)  # .add_field(name="Message", value=text, inline=False)
    if text != '':
        embed.add_field(name="Message", value=text, inline=False)
    else:
        embed.add_field(name="Message", value=DEFAULT_MESSAGE, inline=False)
    extra_parameters['embed'] = embed
    return extra_parameters


async def file_prep(file_info, slack_channel, user_info, text, timestamp, file_save=True):
    EMPTY_EMBED = discord.Embed.Empty
    post_info = {}
    post_info['name'] = file_info['name'].replace('_', '-')
    post_info['link'] = file_info['url_private']
    post_info['title'] = None
    post_info['footer'] = None
    file_save_path = pj(slack_channel, post_info['name'])
    file_attachment = await get_posted_file(post_info['name'], file_save_path, post_info['link'], file_save=file_save)
    if file_attachment is None:
        return EMPTY_EMBED
    elif type(file_attachment) is discord.File:
        return {"file": file_attachment}
    elif os.path.split(file_attachment)[1] != post_info['name']:
         post_info['name'] = os.path.split(file_attachment)[1]
    extra_parameters = {}
    attachment_url = "attachment://{0}".format(post_info['name'])
    extra_parameters['file'] = discord.File(file_attachment, filename=post_info['name'])
    embed_dict = {}
    for label in ('title', 'footer'):
        info = post_info[label]
        if info is not None:
            embed_dict[label] = info
            text += "{0}\n".format(info)
    embed = discord.Embed(**embed_dict) \
        .set_image(url=attachment_url) \
        .set_author(name=user_info['handle'],
                    url=user_info['url'],
                    icon_url=user_info['avatar']) \
        .add_field(name="Time", value=timestamp, inline=False)
    if text != '':
        embed.add_field(name="Message", value=text, inline=False)
    else:
        embed.add_field(name="Message", value=DEFAULT_MESSAGE, inline=False)
    extra_parameters['embed'] = embed
    return extra_parameters


async def get_posted_image(image_name, file_path, url, image_save=True):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as result:
            if image_save:
                if result.status == 200:
                    image = await result.content.read()
                    await convert_image_to_file(file_path, image)
                    return True  # True == Success
                else:
                    print('Download failed')
                    return None
            else:
                if result.status != 200:
                    # return await channel.send(errors.DOWNLOAD_FAILED)
                    print(errors.DOWNLOAD_FAILED)
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
    return file_path


async def get_posted_file(file_name, file_path, url, file_save=True):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as result:
            if file_save:
                if result.status == 200:
                    # await convert_image_to_file(file_path, file_attachment)
                    file_path = await convert_attachment_to_file(file_name, file_path, result)
                    return file_path
                else:
                    print('Download failed')
                    return None
            else:
                if result.status != 200:
                    # return await channel.send(errors.DOWNLOAD_FAILED)
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
