
import html
import logging
import textwrap
from pathlib import Path

from aiogram import Bot, Dispatcher, executor, types
from tabulate import tabulate

from . import api, db
from .config import Config

# TODO: Initialize from main() function. This is not currently possible because the
#   token needs to be available when the #Bot object is created, and it seems that the
#   Bot object cannot be bound to the dispatcher in a delayed fashion.
config = Config.load(Path('config.toml'))
bot = Bot(token=config.api_token)
dp = Dispatcher(bot)


@dp.message_handler(commands=['help', 'hilfe', 'commands', 'befehle'])
@db.async_session
async def send_help(message: types.Message):
    commands = [
        ('/help', 'Diese Hilfe'),
        ('/exercise [name] [link]?', 'Neue Übung mit optionalem Link'),
        ('/alias [alias] [übung]', 'Alias für eine Übung'),
        ('/todos', 'Deine Todos'),
        ('/done [zahl] [übung]', 'Wiederholungen anrechnen'),
        ('/exercises', 'Übungsübersicht')
        ]
    table = '<b>Hilfe</b>'
    for command, description in commands:
        table += '\n\n' + html.escape(command) + '\n' + html.escape(description)
    await message.answer(table, parse_mode = 'html')


@dp.message_handler(commands=['exercise', 'übung'])
@db.async_session
async def add_exercise(message: types.Message):
    args = message.get_args().strip().split(' ')

    if len(args) < 1:
        await message.answer('Zu wenig Argumente, du Otto.')
    elif len(args) > 2:
        await message.answer('Zu viele Argumente, du Otto.')
    else:
        exercise = args[0]
        logging.info(exercise)
        if api.has_exercise(exercise):
            await message.answer('Die Übung {} gibt es bereits.'.format(exercise))
        else:
            link = args[1] if len(args) > 1 else None
            api.add_exercise(exercise, link=link)
            await message.answer('Ich kenne jetzt die Übung {}.'.format(exercise))


@dp.message_handler(commands=['alias'])
@db.async_session
async def add_alias(message: types.Message):
    args = message.get_args().strip().split()

    if len(args) < 2:
        await message.answer('Zu wenig Argumente, du Otto.')
    elif len(args) > 2:
        await message.answer('Zu viele Argumente, du Otto.')
    else:
        alias, exercise_alias = args
        exercise = api.get_exercise_by_alias(exercise_alias)
        if api.has_alias(alias):
            await message.answer('Der Alias {} existiert bereits.'.format(alias))
        elif exercise is None:
            await message.answer('Die Übung {} existiert nicht.'.format(exercise_alias))
        else:
            api.add_alias(alias, exercise)
            await message.answer('{} oder {}? Alles das gleiche!'.format(alias, exercise_alias))


def add_user(user):
    if not api.has_user(user['id']):
        api.add_user(user['id'], user['username'], user['first_name'], user['last_name'])


def tg_link(user_id):
    return 'tg://user?id={}'.format(user_id)


def tg_href(user_id, text):
    return '<a href="{}">{}</a>'.format(tg_link(user_id), text)


@dp.message_handler(commands=['todo', 'todos', 'zutun'])
@db.async_session
async def show_todos(message: types.Message):
    from_user = message['from']
    add_user(from_user)

    todos = api.get_user_todo_reps(from_user['id'])
    dones = api.get_user_reps(from_user['id'])

    stats = [(textwrap.fill(ex, width=12), todos[ex], dones[ex]) for ex in todos]
    table = '<pre>' + html.escape(tabulate(stats, headers=['Übung', 'Todo', 'Done'])) + '</pre>'
    header = '<b>Todos für {}</b>\n\n'.format(tg_href(from_user['id'], from_user['first_name']))
    await message.answer(header + table, parse_mode = "html")


@dp.message_handler(commands=['machma', 'getan', 'done'])
@db.async_session
async def add_reps(message: types.Message):
    args = message.get_args().strip().split()

    if len(args) < 2:
        await message.answer('Zu wenig Argumente, du Otto.')
    elif len(args) > 2:
        await message.answer('Zu viele Argumente, du Otto.')
    else:
        try:
            exercise_alias = args[1]
            exercise = api.get_exercise_by_alias(exercise_alias)
            reps = int(args[0])

            from_user = message['from']
            add_user(from_user)

            if exercise is None:
                await message.answer('Die Übung {} existiert nicht.'.format(exercise_alias))
            else:
                todo = api.get_user_todo_reps_for_exercise(from_user['id'], exercise)
                api.add_to_user_reps(from_user['id'], exercise, reps)
                if reps > todo:
                    user_href = tg_href(from_user['id'], from_user['first_name'])
                    await message.answer('{} weitere {} von {}.'.format(reps - todo, html.escape(exercise), user_href), parse_mode = 'html')
        except ValueError:
            await message.answer('Ne Zahl! Ist das so schwer?')


@dp.message_handler(commands=['exercises', 'übungen'])
@db.async_session
async def show_exercises(message : types.Message):
    exercises = api.get_exercises()
    table = []
    for ex in exercises:
        exercise = html.escape(ex)
        link = exercises[ex]['link']
        table.append(('<a href="{}">{}</a>'.format(link, exercise) if link is not None else exercise,))
    await message.answer(tabulate(table, headers=['Übung']), parse_mode = 'html', disable_web_page_preview=True)


def run():
    executor.start_polling(dp, skip_updates=True)
