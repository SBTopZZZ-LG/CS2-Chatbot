import asyncio
import pydirectinput
import traceback
from nicegui import ui, run
from characterai import PyCAI
from util import *
from numerize import numerize
import random
import json
import requests

current_version = 'v1.2.0'

theme = ui.dark_mode()
theme.enable()

ui.query('.nicegui-content').classes('p-0')
ui.colors(primary='#ec4899')

# c.ai vars
settings_file = 'chatbot_settings.json'
client = None
char_id = None
current_char = None

tgt = None
chat = None

# Game
cs_path = get_cs_path() + '\\game\\csgo\\'
log_dir = cs_path + 'console.log'
exec_dir = cs_path + 'cfg\\message.cfg'
bind_key = 'p'

chat_char_limit = 222
chat_delay = 0.5
last_log = ''
each_key_delay = 0.2


class ToggleButton(ui.button):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state = False
        self.on('click', self.toggle)

    def toggle(self) -> None:
        """Toggle the button state."""
        self._state = not self._state
        self.update()

        if cai_token.value == '':
            ui.notify('Please set a C.AI token!', type='negative')
            tabs.set_value('Settings')
            self._state = not self._state
        elif not current_char:
            ui.notify('Please select a character to use first!', type='negative')
            tabs.set_value('Characters')
            self._state = not self._state
        elif self._state:
            ui.notify('Chatbot is now running!', type='positive', color='pink')
            toggle_active.classes(remove='animate-pulse')
            status_badge.set_visibility(False)
            cai_token.disable()
        else:
            ui.notify('Chatbot has been disabled.', type='warning')
            cai_token.enable()

        self.update()

    def update(self) -> None:
        self.props(f'color={"green" if self._state else "pink"}')
        super().update()


async def handle_chat():
    global last_log
    if toggle_active._state:
        log = get_last_chat(log_dir)

        # Don't respond to same message or when there's no [ALL] chat message
        if log == last_log or log is None:
            return

        data = log.split(': ')

        # Don't respond to self
        if get_last_name_used() in data[0]:
            return

        last_log = log
        message = data[1]

        if mimic_mode_switch.value:
            response_message = ''.join([char.upper() if random.randint(0, 1) else char.lower() for char in message])
        else:
            data = await run.cpu_bound(client.chat.send_message,
                chat['external_id'], tgt, message
            )

            #name = data['src_char']['participant']['name']
            response_message = data['replies'][0]['text']

        # Clean string
        text = response_message.replace('"', "''").replace('\n', ' ')

        # Chunk our message in order to send everything
        texts = [text[i:i + chat_char_limit] for i in range(0, len(text), chat_char_limit)]

        for text in texts:
            with open(exec_dir, 'w', encoding='utf-8') as f:
                f.write(f'say "{text}"')

            # Don't send an input to other windows
            if get_foreground_window_title() == 'Counter-Strike 2':
                if human_mode_switch.value:
                    await asyncio.sleep(each_key_delay * len(text))

                pydirectinput.write(bind_key)
                await asyncio.sleep(chat_delay)


def swap_theme(e):
    if e.value:
        theme.enable()
    else:
        theme.disable()


def load_settings():
    try:
        with open(settings_file) as f:
            settings = json.load(f)
            if settings['token']:
                cai_token.value = settings['token']
    except FileNotFoundError:
        print('No settings file, creating one.')
        with open(settings_file, 'w') as f:
            json.dump({'token': ''}, f)
    except json.JSONDecodeError:
        print('Invalid JSON data, recreating file.')
        with open(settings_file, 'w') as f:
            json.dump({'token': ''}, f)


def check_if_updated():
    try:
        data = requests.get('https://api.github.com/repositories/708269905/releases').json()
        recent_tag = data[0]['tag_name']

        if recent_tag != current_version:
            ui.notify('A new update is available, click <a style="color: #ec4899" href="https://github.com/skelcium/CS2-Chatbot/releases" target="_blank">here</a> to download it.', html=True, close_button='Close', timeout=20000)
    except:
        ui.notify("Failed to check if up-to-date.")

def check_if_admin():
    if not is_running_as_admin():
        ui.notify('Not running as admin, some features <b>may not work</b>.', html=True, close_button='Close', timeout=0, type='warning')


def check_if_condebug():
    if not is_condebug_in_steam_args():
        ui.notify('Could not find <b>-condebug</b> in Steam CS2 launch arguments.', html=True, close_button='Close', timeout=0, type='warning')


def select_character(char):
    if not client:
        ui.notify('Please set a C.AI token!', type='negative')
        tabs.set_value('Settings')
        return

    global char_id
    global tgt
    global current_char

    try:
        client.chat.new_chat(char_id)
    except:
        ui.notify('Failed to create chat, check your token!', type='negative')
        return

    reset_button.enable()
    current_char = char

    if char['avatar_file_name']:
        avatar = 'https://characterai.io/i/80/static/avatars/' + char['avatar_file_name']
    else:
        avatar = 'https://characterai.io/i/80/static/topic-pics/cai-light-on-dark.jpg'

    ui.notify(f'Selected <b>{char["participant__name"]}</b> as your character.', avatar=avatar, color='pink', html=True)
    char_id = char['external_id']

    # Save tgt and history_external_id
    # to avoid making a lot of requests
    global chat
    chat = client.chat.get_chat(char_id)

    participants = chat['participants']

    # In the list of "participants",
    # a character can be at zero or in the first place
    if not participants[0]['is_human']:
        tgt = participants[0]['user']['username']
    else:
        tgt = participants[1]['user']['username']


async def set_token(token, overwrite=False):
    global client

    client = PyCAI(token)
    username = client.user.info()['user']['user']['username']

    if username == 'ANONYMOUS':
        ui.notify('An invalid token has been set!', type='negative')
    else:
        ui.notify(f'Welcome {username}!', type='positive', color='pink')

        # Save correct token
        if overwrite:
            with open(settings_file, 'w') as f:
                json.dump({'token': token}, f)

        await search(query_type='Trending')


async def search(query_type='Search'):

    if cai_token.value == '':
        ui.notify('Please set a C.AI token!', type='negative')
        tabs.set_value('Settings')
        return

    search_btn.disable()

    try:
        if query_type == 'Recommended':
            response = await run.io_bound(client.character.recommended)
            characters = response['recommended_characters']
        elif query_type == 'Recent':
            response = await run.io_bound(client.user.recent)
            characters = response['characters']
        elif query_type == 'Trending':
            response = await run.io_bound(client.character.trending)
            characters = response['trending_characters']
        elif query_type == 'Search':
            response = await run.io_bound(client.character.search, character_input.value)
            characters = response['characters']

        results.clear()

        for character in characters:
            name = character['participant__name']
            if character['avatar_file_name']:
                avatar = 'https://characterai.io/i/80/static/avatars/' + character['avatar_file_name']
            else:
                avatar = 'https://characterai.io/i/80/static/topic-pics/cai-light-on-dark.jpg'

            with results:
                with ui.link().on('click', lambda char=character: select_character(char)).classes('no-underline hover:scale-105 duration-100 active:scale-100 text-pink-600'):
                    with ui.card().tight().classes('w-36 h-48 text-center').classes('shadow-md shadow-black dark:bg-[#121212]'):
                        ui.image(avatar).classes('w-36 h-32')
                        with ui.row().classes('absolute right-2 top-1'):
                            if 'participant__num_interactions' in character:
                                interaction_label = f'🗨️{numerize.numerize(character["participant__num_interactions"])}'
                            else:
                                interaction_label = ''

                            ui.label(interaction_label).classes('text-center drop-shadow-[0_1.2px_1.2px_rgba(0,0,0,1)]')
                        with ui.card_section().classes('h-6 w-full font-bold'):
                            ui.label(name).classes('drop-shadow-[0_1.2px_1.2px_rgba(0,0,0,0.8)]')

        character_count_badge.text = len(characters)
        #ui.notify(f'Found {len(characters)} top results!', type='positive', color='pink')

    except Exception as e:
        traceback_msg = traceback.format_exc()
        ui.notify(traceback_msg)
        search_btn.enable()

    search_btn.enable()

handle_chat_timer = ui.timer(0.1, handle_chat, active=True)

with ui.dialog() as dialog_help_api, ui.card():
    ui.markdown('''
    <h1 style="margin: 0 0 20px 0">Get API Token</h1>
    
    <ol>
        <li> Visit <a style="text-decoration: none; color: hotpink;" target='_blank' href='https://old.character.ai/'>https://old.character.ai/</a> </li>
        <li> Open DevTools in your browser </li>
        <li> Go to Storage → Local Storage → char_token </li>
        <li> Copy value </li>
    </ol>
    ''')

    ui.button('Close', on_click=dialog_help_api.close).props('outline')

with ui.dialog() as dialog_wipe, ui.card():
    ui.markdown('''
    ## Wipe History

    Are you sure you'd like to wipe {current character's} chat history/memory? This cannot be undone.
    ''')

    with ui.row():
        ui.button('Yes', on_click=dialog_wipe.close)
        ui.button('Close', on_click=dialog_wipe.close).props('outline')

with ui.splitter(value=16).classes('w-full h-screen') as splitter:
    with splitter.before:
        ui.icon('chat', color='primary').classes('m-auto text-5xl mt-6')
        with ui.tabs().props('vertical').classes('w-full h-full') as tabs:
            characters = ui.tab('Characters', icon='group')
            with characters:
                character_count_badge = ui.badge('0').classes('absolute mr-3')
            settings = ui.tab('Settings', icon='settings')

        with ui.row().classes('p-2 mx-auto'):
            toggle_active = ToggleButton(icon='power_settings_new').classes('w-11 animate-pulse')
            with toggle_active:
                status_badge = ui.badge('OFF').props('floating').classes('bg-red rounded')
            reset_button = ui.button(icon='restart_alt').classes('w-11 outline').on('click',lambda e: select_character(current_char))
            reset_button.disable()

            with reset_button:
                ui.tooltip("⚠️ Reset Character's memory").classes('bg-red')

    with splitter.after:
        with ui.tab_panels(tabs, value=characters).props('vertical').classes('w-full h-full'):
            with ui.tab_panel(characters).classes('overflow-x-hidden'):
                with ui.row().classes('flex items-center w-full'):
                    character_input = ui.input('Character').on('keypress.enter', search).classes('w-52')
                    search_btn = ui.button(on_click=search, icon='search').classes('outline mt-auto')
                    character_select = ui.select(['Recommended', 'Trending', 'Recent'], value='Trending', on_change=lambda e: search(query_type=e.value)).classes('ml-auto').props('filled')

                ui.separator()
                results = ui.row().classes('flex justify-center')
                with results:
                    ui.chat_message("Hello, recommended characters will be displayed here once you've set a C.AI token.",
                                    name='Skel',
                                    stamp='now',
                                    avatar='https://avatars.githubusercontent.com/u/141345390?s=400&u=16b4e98ca85ea791552d50cdb4aef6491a95e7c9&v=4'
                                    ).props(add="bg-color='pink' text-color='white'")

            with ui.tab_panel(settings):
                with ui.grid(columns=2).classes('w-full'):
                    with ui.card().tight().classes('shadow-sm shadow-black'):
                        with ui.card_section():
                            ui.badge('API')
                            cai_token = ui.input(label='C.AI Token', password=True, on_change=lambda e: set_token(e.value, overwrite=True))

                            with ui.row().classes('mt-5'):
                                ui.button(icon='help', on_click=dialog_help_api.open).props('rounded')

                    with ui.card().tight().classes('shadow-sm shadow-black'):
                        with ui.card_section():
                            ui.badge('Appearance')
                            ui.html('<br>')

                            ui.switch('Dark Theme', on_change=swap_theme, value=True)

                            with ui.row().classes('mt-3') :
                                with ui.button(icon='colorize').props('rounded') as button:
                                    ui.color_picker(on_pick=lambda e: ui.colors(primary=e.color))

                    with ui.card().tight().classes('shadow-sm shadow-black'):
                        with ui.card_section().classes('w-full'):
                            ui.badge('Chatbot')
                            ui.html('<br>')

                            mimic_mode_switch = ui.switch('Mimic Mode')
                            human_mode_switch = ui.switch('Humanized Typing Speed')

                            with mimic_mode_switch:
                                ui.tooltip('Repeat messages with randomly applied capitalization, JuSt LikE ThiS!')

check_if_updated()
check_if_admin()
check_if_condebug()
load_settings()

ui.run(native=True, show=False, window_size=(840, 600), title='CS2 Chatbot', reload=False, show_welcome_message=False)