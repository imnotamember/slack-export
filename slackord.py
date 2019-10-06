import datetime
import json
import os
from os.path import join as pj
import discord
import reformat_slack_data as get_slack
import logging
logging.basicConfig(level=logging.INFO)

fmt = "%Y-%m-%d %H:%M:%S"
GIPHY_BOT = "B2TGYDACQ"

current_folder = os.getcwd()
discord_info_json = pj(current_folder, 'discord_info.json')

with open(discord_info_json) as json_file:
    discord_info = json.load(json_file)[0]
SERVER_ID = discord_info['SERVER_ID']
GUILD_NAME = discord_info['GUILD_NAME']
TOKEN = discord_info['TOKEN']
BACKUP_FOLDER_NAME = discord_info['BACKUP_FOLDER_NAME']

full_path_backup = pj(current_folder, BACKUP_FOLDER_NAME)
slack_channels = os.listdir(full_path_backup)

channel_name = 'shame_cube'

slack_users = get_slack.generate_user_info(full_path_backup)
with open("server_settings.json") as json_file:
    settings = json.load(json_file)
client = discord.Client()


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print(type(client.user))
    print('------')
    print('Slackord is now ready to send messages to Discord!')
    print('Type !mergeslack in the channel you wish to send messages to.')
    guild = await client.fetch_guild(SERVER_ID)
    users = get_slack.get_user_info(guild, slack_users)
    for user, user_info in users.items():
        print(user_info['id'])
        if user_info['id'] is not None:
            discord_user = client.get_user(user_info['id'])
            await discord.ClientUser(discord_user).edit_settings(**settings)


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    guild = message.guild

    # When !mergeslack is typed in a channel, iterate
    # through the JSON file and post the message.
    if message.content.startswith('!mergeslack'):
        discord_users = get_slack.get_user_info(guild, slack_users)
        print("merging slack messages to {0}".format(guild.name))
        await merge_channel(message, discord_users, last=False)

    if message.content.startswith('!lastmergeslack'):
        discord_users = get_slack.get_user_info(guild, slack_users)
        print("merging slack messages to {0}".format(guild.name))
        await merge_channel(message, discord_users, last=True)

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)


async def merge_channel(message, discord_users, last=False):
    if message.channel.name in slack_channels:
        slack_channel = pj(full_path_backup, message.channel.name)
        slack_messages = get_slack.collect_slack_channel_messages(slack_channel)
        print(slack_messages)
        if last:
            slack_messages = [slack_messages[-1]]
            print(slack_messages)
        for slack_message in slack_messages:
            with open(slack_message) as json_file:
                data = json.load(json_file)
                for sub_slack_message in data:
                    message_to_send = None
                    extra_parameters = {}
                    if 'message' in sub_slack_message['type']:
                        slack_user_id = sub_slack_message['user']
                        ts = sub_slack_message['ts']
                        text = sub_slack_message['text']
                        timestamp = datetime.datetime.fromtimestamp(int(float(ts)))
                        message_to_send = "[Time: {0}]\n{1}".format(timestamp, text)
                        user_info = discord_users[slack_user_id]
                        if "has joined" in text:
                            text = user_info['handle'] + text.split('>')[1]
                        if 'bot_id' in sub_slack_message.keys():
                            bot_id = sub_slack_message['bot_id']
                            if bot_id == GIPHY_BOT:
                                giphy_attachment = sub_slack_message['attachments'][0]
                                extra_parameters = await get_slack.image_prep(
                                        giphy_attachment,
                                        slack_channel,
                                        user_info,
                                        text,
                                        timestamp,
                                        image_type='gif')
                        elif 'files' in sub_slack_message.keys():
                            for file_attachment in sub_slack_message['files']:
                                if 'image' in file_attachment['mimetype']:
                                    extra_parameters = await get_slack.image_prep(
                                            file_attachment,
                                            slack_channel,
                                            user_info,
                                            text,
                                            timestamp,
                                            image_type='file')
                                elif 'application' in file_attachment['mimetype']:
                                    extra_parameters = await get_slack.file_prep(
                                            file_attachment,
                                            slack_channel,
                                            user_info,
                                            text,
                                            timestamp)
                        else:
                            embed = discord.Embed(timestamp=timestamp) \
                                .set_author(name=user_info['handle'],
                                            url=user_info['url'],
                                            icon_url=user_info['avatar']) \
                                .add_field(name="Time", value=timestamp, inline=False)
                            if text != '':
                                embed.add_field(name="Message", value=text, inline=False)
                            else:
                                embed.add_field(name='Message', value=get_slack.DEFAULT_MESSAGE, inline=False)
                            extra_parameters = {'embed': embed}
                        # await message.channel.send(message_to_send, **extra_parameters)
                        print(extra_parameters['embed'].fields[1])
                        if extra_parameters is not None:
                            await message.channel.send(**extra_parameters)


client.run(TOKEN)
