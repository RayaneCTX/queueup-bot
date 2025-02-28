import json
import os
import sqlite3
import time

import discord

from bot264.common import create_simple_message


def get_int_env(name):
    env_str = os.getenv(name)
    return 0 if env_str in [None, ''] else int(env_str)


def process_rooms():
    rooms = os.getenv("ROOMS", "{}")
    raw_rooms_dict = json.loads(rooms)
    Permissions.rooms = {int(k): int(v) for k, v in raw_rooms_dict.items() if k and v}


class Permissions:
    rooms = None

    @staticmethod
    async def set_access_to_text_channel(student, ta_voice_channel, state):
        client: discord.Client = DiscordWrapper.client
        ta_channel_id = ta_voice_channel.channel.id
        if ta_channel_id in Permissions.rooms:
            target_channel: discord.TextChannel = client.get_channel(Permissions.rooms[ta_channel_id])
            await target_channel.purge()
            if state:
                await target_channel.set_permissions(student, read_messages=state, send_messages=state)
                message_to_student = """
                You can have a 1 on 1 conversation here with your TA. 
                Hopefully, this session is helpful.
                """
                discord_message = create_simple_message("Hey There {}".format(student.display_name), message_to_student)
                await target_channel.send(embed=discord_message)
            else:
                await target_channel.set_permissions(student, overwrite=None)


def get_db_connection():
    file_location = Db.database_file_location
    if file_location is not None:
        return sqlite3.connect(file_location)
    return None


def create_db():
    Db.database_file_location = os.getenv('DATABASE', None)
    connection = get_db_connection()
    if connection:
        command = """CREATE TABLE IF NOT EXISTS queue (
                            author_id integer PRIMARY KEY, 
                            message_id integer NOT NULL,
                            ta_id integer,
                            wait_time integer,
                            start_time integer
        );"""
        cursor = connection.cursor()
        cursor.execute(command)
        command = """CREATE TABLE IF NOT EXISTS history (
                            id integer PRIMARY KEY, 
                            student_id integer, 
                            ta_id integer,
                            student_name TEXT,
                            ta_name TEXT,
                            start_time integer, 
                            end_time integer,
                            total_time integer,
                            wait_time integer
                            );
                            """
        cursor.execute(command)
        command = """CREATE TABLE IF NOT EXISTS students (
                            student_id integer PRIMARY KEY, 
                            student_name TEXT,
                            num_requests integer,
                            total_time integer, 
                            recorded_date integer 
                            );
                            """
        cursor.execute(command)
        cursor.close()
        connection.close()


class Db:
    database_file_location = None

    @staticmethod
    def is_ta_helping_student(student_id, ta_id):
        student = Db.get_queue_by_student_id(student_id)
        if student is not None:
            return student[2] == ta_id
        return False

    @staticmethod
    def get_queue_by_student_id(student_id):
        connection = get_db_connection()
        if connection:
            command = "SELECT * FROM queue WHERE author_id={};".format(student_id)
            cursor = connection.cursor()
            cursor.execute(command)
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            return data[0] if len(data) > 0 else None
        return None

    @staticmethod
    def get_queue_by_message_id(message_id):
        connection = get_db_connection()
        if connection:
            command = "SELECT * FROM queue WHERE message_id={};".format(message_id)
            cursor = connection.cursor()
            cursor.execute(command)
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            return data[0] if len(data) > 0 else None
        return None

    @staticmethod
    def get_student(student_id):
        connection = get_db_connection()
        if connection:
            command = "SELECT * FROM students WHERE student_id={};".format(student_id)
            cursor = connection.cursor()
            cursor.execute(command)
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            return data[0] if len(data) > 0 else None
        return None

    @staticmethod
    def is_student_in_queue(student_id):
        student = Db.get_queue_by_student_id(student_id)
        return student is not None

    @staticmethod
    def add_student(student_id, message_id):
        connection = get_db_connection()
        if connection:
            command = f"""INSERT INTO queue (author_id, message_id, wait_time)
                      VALUES ({student_id}, {message_id}, {int(time.time())});"""
            cursor = connection.cursor()
            cursor.execute(command)
            connection.commit()
            cursor.close()
            connection.close()

    @staticmethod
    def set_start_time(student_id, ta_id):
        connection = get_db_connection()
        if connection:
            command = f"""UPDATE queue SET start_time={int(time.time())}, ta_id={ta_id}
                        WHERE author_id={student_id};"""
            cursor = connection.cursor()
            cursor.execute(command)
            connection.commit()
            cursor.close()
            connection.close()

    @staticmethod
    def set_wait_time(student_id):
        connection = get_db_connection()
        if connection:
            command = f"""UPDATE queue SET wait_time={int(time.time())} 
                        WHERE author_id={student_id};"""
            cursor = connection.cursor()
            cursor.execute(command)
            connection.commit()
            cursor.close()
            connection.close()

    @staticmethod
    def remove_student(message_id):
        connection = get_db_connection()
        if connection:
            student = Db.get_queue_by_message_id(message_id)
            command = "DELETE FROM queue WHERE message_id={};".format(message_id)
            cursor = connection.cursor()
            cursor.execute(command)

            if student is not None and len(student) >= 5 and \
                    (student[4] not in [None, 0]) and (student[2] not in [None, 0]):
                client: discord.Client = DiscordWrapper.client
                student_user: discord.User = client.get_user(student[0])
                ta_user: discord.User = client.get_user(student[2])
                end_time = int(time.time())
                total_time = end_time - student[4]
                wait_time = student[4] - student[3]
                command = f"""INSERT INTO 
                history (student_id, ta_id, student_name, ta_name, start_time, end_time, total_time, wait_time)
                VALUES ({student[0]}, {student[2]}, "{student_user.display_name}", "{ta_user.display_name}", 
                {student[4]}, {end_time}, {total_time}, {wait_time});
                """
                cursor.execute(command)

                student_usage = Db.get_student(student[0])
                if student_usage is None:
                    command = f"""INSERT INTO students (student_id, student_name, num_requests, total_time) 
                                VALUES ({student[0]}, "{student_user.display_name}", 1, {total_time});"""
                else:
                    command = f"""UPDATE students SET num_requests={student_usage[2] + 1}, 
                                total_time={student_usage[3] + total_time}
                                WHERE student_id={student[0]};"""
                cursor.execute(command)

            connection.commit()
            cursor.close()
            connection.close()


def init_discord_wrapper():
    # Text Channel Settings
    DiscordWrapper.queue_channel = get_int_env('QUEUE_CHANNEL_ID')
    DiscordWrapper.history_channel = get_int_env('HISTORY_CHANNEL_ID')
    DiscordWrapper.bot_channel = get_int_env('BOT_CHANNEL_ID')

    # Voice Channel Settings
    DiscordWrapper.waiting_room = get_int_env("WAITING_ROOM")

    # Role IDS
    DiscordWrapper.uta_role_id = get_int_env('UTA_ROLE_ID')
    DiscordWrapper.gta_role_id = get_int_env('GTA_ROLE_ID')
    DiscordWrapper.prof_role_id = get_int_env('PROFESSOR_ROLE_ID')


class DiscordWrapper:
    client = None
    queue_channel = None
    history_channel = None
    bot_channel = None

    waiting_room = None

    uta_role_id = None
    gta_role_id = None
    prof_role_id = None

    @staticmethod
    def get_queue_channel() -> discord.channel.TextChannel or None:
        if DiscordWrapper.queue_channel != 0:
            return DiscordWrapper.client.get_channel(DiscordWrapper.queue_channel)
        return None

    @staticmethod
    def get_waiting_room() -> discord.channel.VoiceChannel or None:
        if DiscordWrapper.waiting_room != 0:
            return DiscordWrapper.client.get_channel(DiscordWrapper.waiting_room)
        return None

    @staticmethod
    async def move_user_to_office_hours(user_id: discord.member.Member, ta_voice_state):
        if ta_voice_state is None:
            return False
        dest_voice_channel: discord.channel.VoiceChannel = ta_voice_state.channel
        waiting_room: discord.channel.VoiceChannel = DiscordWrapper.get_waiting_room()
        if None in [waiting_room, user_id.voice]:
            return False
        await user_id.move_to(dest_voice_channel)
        await Permissions.set_access_to_text_channel(user_id, ta_voice_state, True)
        return True

    @staticmethod
    async def move_user_to_waiting_room(user_id, ta_voice_state):
        await Permissions.set_access_to_text_channel(user_id, ta_voice_state, False)
        waiting_room: discord.channel.VoiceChannel = DiscordWrapper.get_waiting_room()
        if None in [waiting_room, user_id.voice]:
            return False
        await user_id.move_to(waiting_room)
        return True

    @staticmethod
    async def disconnect_user(user_id, ta_voice_state):
        await Permissions.set_access_to_text_channel(user_id, ta_voice_state, False)
        if user_id.voice is not None:
            await user_id.move_to(None)

    @staticmethod
    def is_emoji_channels(channel_id):
        return channel_id in [DiscordWrapper.queue_channel, DiscordWrapper.history_channel]

    @staticmethod
    def is_admin_role(role: discord.role.Role):
        return role.id in [DiscordWrapper.uta_role_id, DiscordWrapper.gta_role_id, DiscordWrapper.prof_role_id]

    @staticmethod
    def is_admin(member):
        if type(member) != discord.member.Member:
            return False
        for i in member.roles:
            if DiscordWrapper.is_admin_role(i):
                return True
        return False

    @staticmethod
    async def add_history(message: discord.message.Message):
        embed_message = create_simple_message(message.author.name, message.content)
        if DiscordWrapper.history_channel is not None:
            history_channel: discord.TextChannel = DiscordWrapper.client.get_channel(DiscordWrapper.history_channel)
            message = await history_channel.send(embed=embed_message)
            for i in ["🔄", "❌"]:
                await message.add_reaction(i)
