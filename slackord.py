import json
import logging
import os
from os.path import join as pj
from pprint import pprint
import discord

import reformat_slack_data as get_slack

logging.basicConfig(level=logging.INFO)

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
    logging.log(level=logging.INFO, msg='Logged in as')
    logging.log(level=logging.INFO, msg=client.user.name)
    logging.log(level=logging.INFO, msg=client.user.id)
    logging.log(level=logging.INFO, msg=type(client.user))
    logging.log(level=logging.INFO, msg='------')
    logging.log(level=logging.INFO, msg='Slackord is now ready to send messages to Discord!')
    logging.log(level=logging.INFO, msg='Type !mergeslack in the channel you wish to send messages to.')
    # guild = await client.fetch_guild(SERVER_ID)
    guild = client.get_guild(SERVER_ID)
    get_slack.users = get_slack.get_user_info(guild, slack_users)
    for user, user_info in get_slack.users.items():
        logging.log(level=logging.INFO, msg="{0}\t\t{1}".format(user_info['id'], user_info['discord_handle']))
        # # The following line was an attempt to auto-config all users settings, but can't actually do that.
        # # Can only alter current user's settings.
        # if user_info['id'] is not None:
        #     discord_user = client.get_user(user_info['id'])
        # await discord.ClientUser(discord_user).edit_settings(**settings)


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
        logging.log(level=logging.INFO, msg="merging slack messages to {0}".format(guild.name))
        await merge_channel(message, discord_users, last=False)

    if message.content.startswith('!lastmergeslack'):
        discord_users = get_slack.get_user_info(guild, slack_users)
        logging.log(level=logging.INFO, msg="merging slack messages to {0}".format(guild.name))
        await merge_channel(message, discord_users, last=True)

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)


async def merge_channel(message, discord_users, last=False):
    if message.channel.name in slack_channels:
        slack_channel = pj(full_path_backup, message.channel.name)
        slack_messages = get_slack.collect_slack_channel_messages(slack_channel)
        logging.log(level=logging.INFO, msg="Slack Message Files:\n\t{}".format("\n\t".join(slack_messages)))
        if last:
            slack_messages = [slack_messages[-1]]
            logging.log(level=logging.INFO, msg=slack_messages)
        for slack_message in slack_messages:
            await import_message(slack_message, discord_users, slack_channel, message.channel)


async def import_message(message, discord_users, slack_channel, discord_channel):
    with open(message) as json_file:
        data = json.load(json_file)
        for sub_slack_message in data:
            processed_message = await get_slack.process_message(sub_slack_message, discord_users, slack_channel)
            if processed_message != {}:
                pprint(processed_message)
                await discord_channel.send(**processed_message)


client.run(TOKEN)
