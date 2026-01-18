"""
Keyboard Definitions Module

Defines Telegram reply keyboards and inline keyboards for the bot.
"""

from typing import List

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Get the main menu keyboard with quick action buttons.
    
    Returns a ReplyKeyboardMarkup with:
    - /new - Start new session
    - /status - Check session status
    - /help - Show help
    """
    keyboard = [
        [KeyboardButton("/new"), KeyboardButton("/status")],
        [KeyboardButton("/help")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Type a message or choose a command...",
    )


def get_session_keyboard() -> ReplyKeyboardMarkup:
    """
    Get keyboard for active session.
    
    Adds option to end the current session.
    """
    keyboard = [
        [KeyboardButton("/new"), KeyboardButton("/status")],
        [KeyboardButton("/end"), KeyboardButton("/help")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_help_keyboard() -> ReplyKeyboardMarkup:
    """
    Get help/information keyboard.
    """
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("/help")],
        [KeyboardButton("/cancel")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Get a simple cancel keyboard.
    """
    keyboard = [
        [KeyboardButton("/cancel")],
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Return a keyboard remove action.
    
    Use this to hide the custom keyboard.
    """
    return ReplyKeyboardRemove()
