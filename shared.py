import secrets
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# --- Shared Voting Data ---
vote_data = {}  # message_id: {'working': int, 'not_working': int, 'voters': set, 'emoji_pair': tuple}
last_posted_link = None

# --- Emoji Pairs ---
EMOJI_PAIRS = [
    ("\U0001F7E2", "\U0001F534"), ("\u2705", "\u274C"), ("\U0001F525", "\U0001F61E"), ("\U0001F4AF", "\U0001F635"), ("\U0001F60E", "\U0001F62D"), ("\U0001F680", "\U0001F6D1"), ("\U0001F31F", "\U0001F44E"), ("\U0001F947", "\U0001F940"), ("\U0001F340", "\U0001FAA6"), ("\U0001F389", "\U0001F62C")
]

# --- Message Formatting ---
def format_canva_post_message(latest_link, working_votes=None, not_working_votes=None, emoji_pair=None):
    if emoji_pair is None:
        emoji_pair = secrets.choice(EMOJI_PAIRS)
    good_emoji, bad_emoji = emoji_pair
    goal_num = random.randint(4, 10)
    msg = (
        f"{good_emoji} <b>New Canva Pro Team Link:</b>\n"
        f"<a href='{latest_link}'>{latest_link}</a>\n\n"
        "\U0001F514 <i>Unmute for instant access!</i>\n"
        "\U0001F5BC\uFE0F <b>Proof:</b> After joining, send a screenshot to <a href='https://t.me/aenzBot'>@aenzBot</a>.\n\n"
        f"\U0001F3AF <b>Goal:</b> Let's hit <b>{goal_num}</b> reactions! \U0001F680\n"
        "<code>React below to help others know if it works!</code>"
    )
    if working_votes is None:
        working_votes = 0
    if not_working_votes is None:
        not_working_votes = 0
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{good_emoji} Working ({working_votes})", callback_data=f"vote_working|{good_emoji}|{bad_emoji}"),
            InlineKeyboardButton(f"{bad_emoji} Not Working ({not_working_votes})", callback_data=f"vote_not_working|{good_emoji}|{bad_emoji}")
        ],
        [
            InlineKeyboardButton("\U0001F4E3 Share Channel", url="https://t.me/share/url?url=https://t.me/CanvaProInviteLinks&text=\u2705 Unlock daily Canva Pro team links! Totally free, always fresh. \u2764\uFE0F"),
            InlineKeyboardButton("Join Backup \u26A0\uFE0F", url="https://t.me/+ejp2_sjBtJczY2I9")
        ]
    ])
    return msg, keyboard, emoji_pair
