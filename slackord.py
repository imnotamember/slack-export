import json
import os
from os.path import join as pj
import discord
import reformat_slack_data as get_slack

discord_info = json.load('discord_info.json')
SERVER_ID = discord_info['SERVER_ID']
GUILD_NAME = discord_info['GUILD_NAME']
TOKEN = discord_info['TOKEN']

current_folder = os.getcwd()
backup_path = 'Vamp Lab Slack export Sep 9 2016 - Sep 7 2019'
full_path_backup = pj(current_folder, backup_path)
slack_channels = os.listdir(full_path_backup)

channel_name = 'shame_cube'

slack_users = get_slack.generate_user_info(full_path_backup)
print(slack_users)

client = discord.Client()

# run_once = discord.Client()
#
#
# # @run_once.event
# async def convert_users_slack_to_discord():
# # async def on_ready():
#     print('start getting user info')
#     # global users
#     guild = discord.utils.get(run_once.guilds, name=GUILD_NAME)
#     # run_once.slack_mapping = get_slack.get_user_info(guild=guild, slack_backup_path=full_path_backup)
#     return get_slack.get_user_info(guild=guild, slack_backup_path=full_path_backup)
#     # print(run_once.users)
#     # print('stop getting user info')
#     # print('stop async')
#     # print('async stopped')
#
#
# future = run_once.loop.create_task(convert_users_slack_to_discord())
# run_once.run(TOKEN)
# print(run_once.users)
# print(run_once.slack_mapping)
# print(future)
# quit()


# bot = commands.Bot(command_prefix='!')

# # Change the JSON file name in the quoted field below.
# with open(file_name) as json_file:
#     print(file_name)
#     data = json.load(json_file)
#     print(data)
#     for message in data:
#         # Print the messages we'll output to Discord
#         # from the Slack JSON file into console for the user to see.
#         if "real_name" in message.keys() and "datetime" in message.keys(
#         ) and "text" in message.keys():
#             print((message["datetime"]) + (': ') + (message["real_name"]) + (
#                 ': ') + (message["text"]))
#             print (' ')
#         elif "bot_message" in message.keys() and "text" in message.keys():
#             print ("%s BOT MESSAGE" % (message["bot_message"]) + (
#                 ': ') + (message["text"]))


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Slackord is now ready to send messages to Discord!')
    print('Type !mergeslack in the channel you wish to send messages to.')


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    # When !mergeslack is typed in a channel, iterate
    # through the JSON file and post the message.
    if message.content.startswith('!mergeslack'):
        print("merging slack message")
        if message.channel.name in slack_channels:
            slack_channel = pj(full_path_backup, message.channel.name)
            slack_messages = get_slack.collect_slack_channel_messages(slack_channel)
            for slack_message in slack_messages:
                with open(slack_message) as json_file:
                    data = json.load(json_file)
                    for sub_slack_message in data:
                        messageToSend = None
                        extra_paramaters = {}
                        user_url = discord.Embed.Empty
                        print(sub_slack_message.keys())
                        if 'message' in sub_slack_message['type']:
                            # if "user" in sub_slack_message.keys() and "ts" in sub_slack_message.keys() and "text" in sub_slack_message.keys():
                            user = sub_slack_message['user']
                            ts = sub_slack_message['ts']
                            text = sub_slack_message['text']
                            # user_info = get_slack.get_user_info(full_path_backup, user)
                            user_info = users[user]
                            # messageToSend = "[Time: {0}]\n({1}){2}: {3}".format(ts,
                            #                                             user_info['real_name'],
                            #                                             user_info['display_name'],
                            #                                             text)
                            try:
                                for files in sub_slack_message['files']:
                                    if 'image' in files['mimetype']:
                                        # messageToSend = "Found and image!\n"
                                        image_name = files['name'].replace('_', '-')
                                        image_save_path = pj(slack_channel, image_name)
                                        image_link = files['url_private']
                                        image = get_slack.get_posted_image(image_save_path, image_link)
                                        print(image_name, image_link)
                                        attachment_url = "attachment://{0}".format(image_name)
                                        extra_paramaters['file'] = discord.File(image_save_path, filename=image_name)
                                        embed = discord.Embed() \
                                            .set_image(url=attachment_url) \
                                            .set_author(name=user_info['handle'],
                                                        url=user_url,
                                                        icon_url=user_info['avatar'])
                                        # embed.set_image(url=attachment_url)
                                        extra_paramaters['embed'] = embed
                                    else:
                                        # extra_paramaters['embed'] = discord.Embed(image={'url': image_url})
                                        pass
                            except KeyError:
                                pass
                            # print(messageToSend)
                        elif "bot_message" in sub_slack_message.keys() and "text" in sub_slack_message.keys():
                            messageToSend = '{0["bot_message"]}: {0["text"]}: BOT MESSAGE'.format(sub_slack_message)
                            # print(messageToSend)
                        if messageToSend is not None:
                            await message.channel.send(messageToSend, **extra_paramaters)

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)


async def merge_channel(message, slack_message):
    # print(message)
    # print(slack_message)
    return_messages = []
    return return_messages


# # When !mergeslack is typed in a channel, iterate
# # through the JSON file and post the message.
# @bot.command(pass_context=True)
# async def mergeslack(ctx):
#     with open(file_name) as json_file:
#         data = json.load(json_file)
#         for message in data:
#             if "real_name" in message.keys() and "datetime" in message.keys(
#             ) and "text" in message.keys():
#                 messageToSend = ((message["datetime"]) + (': ') + (
#                     message["real_name"]) + (': ') + (message["text"]))
#                 await ctx.send(messageToSend)
#             elif "bot_message" in message.keys() and "text" in message.keys():
#                 messageToSend = ("%s BOT MESSAGE" % (
#                     message["bot_message"]) + (': ') + (message["text"]))
#                 await ctx.send(messageToSend)


# client.loop.create_task(convert_users_slack_to_discord())
# Insert the Discord bot token into the quoted section below
client.run(TOKEN)
