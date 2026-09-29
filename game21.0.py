import json
import copy
import random
import os
import time
import sys

# The game loop loads pygame only when it is started.  This keeps narrative and
# game-state helpers importable by tools even when the optional audio dependency
# is not installed.
pygame = None

# `msvcrt` is available only on Windows.  Keeping input behind one helper makes
# the terminal game usable on Linux/macOS as well (and avoids importing a
# Windows-only module there).
if os.name == "nt":
    import msvcrt

    def get_key():
        return msvcrt.getch().lower()
else:
    import termios
    import tty

    def get_key():
        """Read one key press from a POSIX terminal and return it as bytes."""
        file_descriptor = sys.stdin.fileno()
        previous_settings = termios.tcgetattr(file_descriptor)
        try:
            tty.setraw(file_descriptor)
            return sys.stdin.buffer.read(1).lower()
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, previous_settings)

SAVE_FILE = "save_data.json"
SAVE_DIR = "saves"
SAVE_DIR2 = "system"
#Внутриигровое время
class GameTime:
    global player
    def __init__(s, years=1, months=6, hours=5, minutes=0, days=1):
        s.years = years
        s.months = months
        s.hours = hours
        s.minutes = minutes
        s.days = days
    def time_up(s, minutes):
        global player
        if player["days"] == 1 and player["dobav"]==False:
            locations["Чайный Дом"]["actions"].insert(0, "войти_в_чайный_дом")
            player["dobav"] = True
        #if player["days_befor_disaster"]:
        #    demons_are_coming()
        if player["level"] >= 2 and not player["trigger_for_abyss"]:
            mine_actions = locations["Заброшенные Шахты"]["actions"]
            if "исследовать_пещеры" not in mine_actions:
                mine_actions.append("исследовать_пещеры")
            player["trigger_for_abyss"] = True
        check_house()
        s.minutes += minutes
        if player["stamina"] <= 0:
            sleep_with_danger()
            location_menu()
        while s.minutes >= 60:
            s.minutes -= 60
            s.hours += 1
        while s.hours >= 24:
            s.hours -=24
            s.days += 1
            player["days_befor_disaster"] -= 1
            print("Наступил новый денёк!")
            player["days"] += 1
        while s.days > 30:
            s.days -= 30
            s.months += 1
        while s.months > 12:
            s.months -= 12
            s.years += 1
        if player["days"] == 1 and not player["nado"]:
            update_quest_availability()
            player["nado"] = True
        stamina_reg = (minutes // 60) * 5
        player["stamina"] = min(player["stamina"] + stamina_reg, player["max_stamina"])
    def gtime(s):
        return f"{s.hours:02}:{s.minutes:02}"
    def todic(s):
        return {
            "years": s.years,
            "months": s.months,
            "days": s.days,
            "hours": s.hours,
            "minutes": s.minutes
        }
    def gdate(s):
        month_str = month_name.get(s.months, "Неизвестный месяц")
        return f"{s.years} Год, {month_str}, {s.days} День"

#game_time.time_up(minutes) Использовать для изменения времени

game_time = GameTime()
a = {
    "main": False,
    "dialog": False,
    "location": False,
    "begin": False,
    "hram": False,
    "abyss": False,
    "battle": False
    }

def remove_last_lines(n):
    for i in range(n):
        print("\033[F\033[K", end='')


def print_menu(options, index, zaglav=None):
    if zaglav:
        print(f"{zaglav}")
    for i, option in enumerate(options):
        prefix = "  > " if i == index else "  "
        print(f"{prefix}{option}")
def demons_are_coming():
    slow_print("Демоническая энергия становится сильнее. Нужно остановить Кайто.")
def handle_menu(options, glav=None):
    index = 0
    print_menu(options, index, glav)
    while True:
        key = get_key()
        if glav:
            if key == b'w' and index >= 0:
                if index == 0:
                    index = len(options)-1
                else:
                    index -= 1
                remove_last_lines(len(options)+1)
                print_menu(options, index, glav)
            elif key == b's' and index <= len(options)-1:
                if index >= len(options)-1:
                    index = 0
                else:
                    index += 1
                remove_last_lines(len(options)+1)
                print_menu(options, index, glav)
            elif key == b'\r':
                return index
        else:
            if key == b'w' and index >= 0:
                if index == 0:
                    index = len(options)-1
                else:
                    index -= 1
                remove_last_lines(len(options))
                print_menu(options, index, glav)
            elif key == b's' and index <= len(options)-1:
                if index >= len(options)-1:
                    index = 0
                else:
                    index += 1
                remove_last_lines(len(options))
                print_menu(options, index, glav)
            elif key == b'\r':
                return index
#В диалги
def dial():
    while True:
        opt = [
            "Продолжить",
            "Словарь игры"
        ]
        choice = handle_menu(opt)
        clear()
        if choice == -1:
            continue
        if choice == 0:
            clear()
            break
        elif choice == 1:
            dictionary()
            clear()
            break
chanels_for_music = {}
def play_sound_with_tag(sound_file, tag, lop=0, volume=1.0):
    sound = pygame.mixer.Sound(sound_file)
    sound.set_volume(volume)
    channel = pygame.mixer.find_channel()
    if channel:
        channel.play(sound, loops=lop)
        chanels_for_music[tag] = (channel, sound)
def set_volume_by_tag(tag, volume):
    if tag in chanels_for_music:
        channel, sound = chanels_for_music[tag]
        sound.set_volume(volume)
        channel.set_volume(volume)
def stop_sound_by_tag(tag, stop=2000):
    if tag in chanels_for_music:
        channel, sound = chanels_for_music[tag]
        if channel.get_busy():
            if stop > 0:
                channel.fadeout(stop)
            else:
                channel.stop()
        del chanels_for_music[tag]
def loading_screen(dlitelnost=2, message="Загрузка"):
    frames = ["/", "-", "\\", "|"]
    end_time = time.time() + dlitelnost
    while time.time() < end_time:
        for frame in frames:
            print(f"\r{message} {frame}", end="", flush=True)
            time.sleep(0.1)
    print("\r" + " " * 50 + "\r", end="", flush=True)
#месяцы
month_name = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь"
}
# Игрок
# Не забывать добавлять переменные в файл с сохранием.
player = {
    "total_defense":0,
    "dobav":False,
    "nado": False,
    "days": 0,
    "name": None,
    "level": 1,
    "stamina": 100,
    "max_stamina": 100,
    "xp": 0,
    "xp_tn": 50,
    "hp": 100,
    "max_hp": 100,
    "money": 10000, #По умолчанию поставить 100 монет№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№№
    "inventory": [],
    "equipped_weapon": None,
    "head": None,
    "body": None,
    "legs": None,
    "house_build": False,
    "house_day": None,
    "house_available": False,
    "blocking": False,
    "temp": 1.0,
    "bad_ending": False, #наверное можно удалить🤣
    "pervaya_molitva": False, #для первой молитвы
    "exp_heat": 0, #для расчета жары
    "abyss_floor": 1, #уровень подземелья
    "halfgod_power": False, #сила полубога для конца
    "first_come_to_abyss": True, #первое появление в подземелье
    "abyss_kills": 0, #убийства в подземелье
    "abyss_were_found": False, #найдено ли подземелье
    "trigger_for_abyss": False, #для добавления действия 
    "days_befor_disaster": 360, #дни до конца игры
    "skills_act": False, #можно ли использовать скилы в бою 
    "you_can_run": False #можно ли сбежать с боя
    }
# Used to fill fields that were added after an older save was created.
DEFAULT_PLAYER = player.copy()
music = {
    "VOLUME_MUSIC" : 0.6,
    "VOLUME_SFX" : 0.8,
    "music": False,
    "SFX": False,
    "text_speed": 0.05
}
def settings_save():
    global music
    savings = {
        "music": music
    }
    save_path = os.path.join(SAVE_DIR2, "settings.json")
    try:
        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(savings, f, ensure_ascii=False)
            print("Настройки сохранены!")
    except Exception as e:
        print(f"Ошибка сохранения: {str(e)}")
    input("Нажмите Enter, чтобы продолжить...")
    clear()
#Имя
def name_creation():
    name = input("Введите имя персонажу: ")
    return name

current_location = "Храм Двух Лун"

def make_quest(description, reward, requires, stages, available=False):
    """Create a quest entry with a consistent state and location-bound stages."""
    return {
        "description": description,
        "reward": reward,
        "requires": requires,
        "available": available,
        "started": False,
        "completed": False,
        "stages": {
            stage_id: {
                "hint": hint,
                "location": location,
                "started": False,
                "completed": False,
            }
            for stage_id, hint, location in stages
        },
    }


quests = {
    "Пробуждение в Храме": make_quest("Понять, почему ГГ оказался в Мире Теней, и пережить первое нападение они.", {"gold": 50, "xp": 10}, [], [("dialog", "Выслушать Аямэ в Храме Двух Лун.", "Храм Двух Лун"), ("training", "Пройти тренировку с Аямэ.", "Храм Двух Лун"), ("first_battle", "Победить первого они в Бамбуковом Лесу.", "Бамбуковый Лес")], True),
    "Знак хризантемы": make_quest("Восстановить алтарь у священного источника и узнать значение печати ГГ.", {"gold": 80, "xp": 20}, ["Пробуждение в Храме"], [("tablets", "Собрать таблички с именами погибших на Рисовых Полях.", "Рисовые Поля"), ("altar", "Очистить алтарь у источника.", "Храм Двух Лун")]),
    "Песня Трех Источников": make_quest("Собрать реликвии стихий, чтобы открыть путь к мастеру Рэндзиро.", {"gold": 200, "xp": 30}, ["Знак хризантемы"], [("dialog", "Поговорить с Аямэ в Чайном Доме.", "Чайный Дом"), ("heart_of_water", "Получить Сердце Воды в Саду Лунных Водопадов.", "Сад Лунных Водопадов"), ("obsidian_dagger", "Найти Обсидиановый Кинжал в Заброшенных Шахтах.", "Заброшенные Шахты"), ("fan_of_winds", "Вернуть Веер Ветров в Рыбацкой Деревне.", "Рыбацкая Деревня")]),
    "Голос в тумане": make_quest("Расследовать появление призрачных воинов и найти колокольчик-фурин.", {"gold": 90, "xp": 25}, ["Песня Трех Источников"], [("investigate", "Исследовать туман на Рисовых Полях.", "Рисовые Поля"), ("furin", "Решить судьбу колокольчика-фурин.", "Рисовые Поля")]),
    "Дорога к мастеру": make_quest("Пройти испытания ками и найти убежище мастера Рэндзиро.", {"gold": 120, "xp": 35}, ["Песня Трех Источников"], [("kami", "Решить загадку ками в Бамбуковом Лесу.", "Бамбуковый Лес"), ("master", "Встретиться с Рэндзиро на Горе Амацу.", "Гора Амацу")]),
    "Кровь Черного Дракона": make_quest("Добыть осколок Гнева из Заброшенных Шахт.", {"gold": 160, "xp": 45}, ["Дорога к мастеру"], [("mine", "Спуститься к проклятому шахтёру.", "Заброшенные Шахты"), ("fragment", "Очистить или забрать осколок Гнева.", "Заброшенные Шахты")]),
    "Танец лисьих огней": make_quest("Пройти иллюзии кицунэ и получить осколок Страха.", {"gold": 170, "xp": 45}, ["Кровь Черного Дракона"], [("setsu", "Поговорить с Сэцу в Чайном Доме.", "Чайный Дом"), ("illusions", "Пройти иллюзии кицунэ.", "Бамбуковый Лес")]),
    "Песня моря": make_quest("Помочь духу невесты Мидори и получить осколок Тоски.", {"gold": 180, "xp": 50}, ["Танец лисьих огней"], [("kimono", "Найти свадебное кимоно в Порту Алой Луны.", "Порт Алой Луны"), ("midori", "Вернуть кимоно Мидори в Рыбацкой Деревне.", "Рыбацкая Деревня")]),
    "Клятва сакуры": make_quest("Заручиться поддержкой клана самураев.", {"gold": 200, "xp": 55}, ["Песня моря"], [("champion", "Принять вызов чемпиона на Горе Амацу.", "Гора Амацу"), ("oath", "Заключить клятву сакуры.", "Храм Двух Лун")]),
    "Шёпот ниндзя": make_quest("Раскрыть заговор и спасти Томоэ от яда.", {"gold": 200, "xp": 55}, ["Песня моря"], [("clues", "Собрать улики на Улице Красных Фонарей.", "Улица Красных Фонарей"), ("rescue", "Спасти Томоэ в Деревне Ниндзя.", "Деревня Ниндзя")]),
    "Сердце кузнеца": make_quest("Помочь Гэну выковать оружие из драконьей стали.", {"gold": 220, "xp": 60}, ["Песня моря"], [("ore", "Добыть драконью сталь в Заброшенных Шахтах.", "Заброшенные Шахты"), ("forge", "Выковать оружие в Кузнице Драконьей Стали.", "Кузница Драконьей Стали")]),
    "Тень Предательства": make_quest("Найти советника Аяме, который тайно служит Кайто.", {"gold": 220, "xp": 60}, ["Клятва сакуры", "Шёпот ниндзя", "Сердце кузнеца"], [("clues", "Собрать улики в Чайном Доме.", "Чайный Дом"), ("choice", "Решить судьбу Норио в Храме Двух Лун.", "Храм Двух Лун")]),
    "Последний закат": make_quest("Удержать храм во время первой волны вторжения.", {"gold": 250, "xp": 70}, ["Тень Предательства"], [("defense", "Защитить Храм Двух Лун.", "Храм Двух Лун")]),
    "Проклятый ритуал": make_quest("Проникнуть в лагерь Кайто и разрушить питающий Врата алтарь.", {"gold": 280, "xp": 80}, ["Последний закат"], [("infiltrate", "Проникнуть в Логово Кайто.", "Логово Кайто"), ("altar", "Разрушить или поглотить силу алтаря.", "Логово Кайто")]),
    "Лицо предателя": make_quest("Сразиться с Кайто на вершине пагоды.", {"gold": 350, "xp": 100}, ["Проклятый ритуал"], [("duel", "Подняться на Пагоду Кайто и победить его.", "Пагода Кайто")]),
    "Жертва зеркала": make_quest("Решить судьбу Зеркала Амацу.", {"gold": 0, "xp": 100}, ["Лицо предателя"], [("mirror", "Выбрать судьбу Зеркала у Врат Теней.", "Врата Теней")]),
    "Прощание с Аяме": make_quest("Провести последний ритуал вместе с Аяме.", {"gold": 0, "xp": 150}, ["Жертва зеркала"], [("ritual", "Провести ритуал у Врат Теней.", "Врата Теней")]),
    "Доспехи забытых воинов": make_quest("Собрать части легендарного доспеха и вернуть имена павшим.", {"gold": 100, "xp": 30}, ["Знак хризантемы"], [("helm", "Найти шлем на Рисовых Полях.", "Рисовые Поля"), ("cuirass", "Найти кирасу в Заброшенных Шахтах.", "Заброшенные Шахты"), ("return", "Вернуть доспех храму.", "Храм Двух Лун")]),
    "Дом для дзасики-вараси": make_quest("Вернуть духу ребёнка его игрушку.", {"gold": 70, "xp": 20}, ["Знак хризантемы"], [("toy", "Найти игрушку на Рынке Двух Ликов.", "Рынок Двух Ликов"), ("home", "Отнести игрушку в Дом.", "Дом")]),
    "Колокол без рассвета": make_quest("Снять проклятие с храма в Порту Алой Луны.", {"gold": 110, "xp": 35}, ["Песня Трех Источников"], [("bell", "Осмотреть проклятый колокол в Порту Алой Луны.", "Порт Алой Луны"), ("cleanse", "Очистить колокол в Храме Двух Лун.", "Храм Двух Лун")]),
    "Письма Рэндзиро": make_quest("Найти пять писем мастера к Кайто, чтобы открыть путь к пощаде.", {"gold": 150, "xp": 45}, ["Дорога к мастеру"], [("first", "Найти первое письмо на Горе Амацу.", "Гора Амацу"), ("second", "Найти второе письмо в Чайном Доме.", "Чайный Дом"), ("third", "Найти третье письмо в Порту Алой Луны.", "Порт Алой Луны"), ("fourth", "Найти четвёртое письмо в Заброшенных Шахтах.", "Заброшенные Шахты"), ("fifth", "Найти последнее письмо в Логове Кайто.", "Логово Кайто")]),
}

# Runtime registry for location actions created by active quest stages.
STORY_ACTIONS = {}
DEFAULT_QUESTS = copy.deepcopy(quests)


def merge_loaded_quests(saved_quests):
    """Keep old save progress while adding quests and fields introduced later."""
    merged_quests = copy.deepcopy(DEFAULT_QUESTS)
    for quest_name, saved_quest in saved_quests.items():
        if quest_name not in merged_quests:
            merged_quests[quest_name] = saved_quest
            continue
        target = merged_quests[quest_name]
        for key, value in saved_quest.items():
            if key != "stages":
                target[key] = value
        for stage_name, saved_stage in saved_quest.get("stages", {}).items():
            if stage_name in target["stages"]:
                target["stages"][stage_name].update(saved_stage)
    return merged_quests

sub_quests = {}



# Враги
enemies = [
    {"name": "Самурай-предатель", "hp": 60, "damage": (12, 18), 
     "loot": ["дамасская сталь", "шелк"], "gold": (20, 40)},
    {"name": "Демон Они", "hp": 80, "damage": (15, 25),
     "loot": ["зачарованная сталь", "пергамент"], "gold": (30, 50)},
    {"name": "Дракон-рони́н", "hp": 120, "damage": (20, 35),
     "loot": ["драконья чешуя", "золото"], "gold": (100, 200)},
    {"name": "Мастер каллиграфии", "hp": 65, "damage": (10, 15),
     "loot": ["краска", "рисовые волокна"], "gold": (80, 150)},
    {"name": "Бакэмоно-бродяга", "hp": 55, "damage": (10, 16), 
    "loot": ["гнилой бамбук", "тряпье онрё"], "gold": (15, 30)},
    {"name": "Кодама-воин", "hp": 70, "damage": (12, 20), 
    "loot": ["древесная смола", "лист сакуры"], "gold": (25, 50)},
    {"name": "Дзасики-вараши", "hp": 45, "damage": (8, 14), 
    "loot": ["детская игрушка", "сломанный оберег"], "gold": (10, 20)}
]


#боссы
bos = {
    "Логово Кайто": {
        "name": "Они-Обаримен", 
        "hp": 200, 
        "damage": (35, 55), 
        "loot": ["Рог они", "Пламя Ямато"], 
        "gold": (300, 500),
        "special_attack": "Удар Тьмы",
        "dialog": "Ты осмелился бросить вызов Повелителю всего живого?!"
    },
    "Сад Лунных Водопадов": {
        "name": "Дух Водопада", 
        "hp": 150,
        "damage": (25, 40), 
        "loot": ["Лунный Кристалл"], 
        "gold": (200, 300),
        "special_attack": "Цунами",
        "dialog": "Воды поглотят твою душу!"
    }
}

# Рецепты крафта
weapon_recipes = {
    "Катана": {"дамасская сталь": 3, "шелк": 2},
    "Нагината": {"металл": 3, "бамбук": 4},
    "Лук": {"гибкий бамбук": 4, "шелковая тетива": 1},
    "Кусунгобу": {"зачарованная сталь": 5},
    "Боевой веер": {"сталь": 2, "пергамент": 3},
    "Копьё": {"бамбук": 4, "бронза": 3},
    #Самурай Рассвета
    "Рассветная Катана": {"дамасская сталь": 5, "золотая фольга": 3},
    "Солнечный Нагината": {"дамасская сталь": 4, "шипы": 2},
    #Теневой Странник
    "Коготь Тени": {"зачарованная сталь": 3, "чернила тэнгу": 2},
    "Клинок Лунного Света": {"ночной шелк": 2, "обсидиан": 1},
    #Драконий Кузнец 
    "Гнев Дракона": {"драконья чешуя": 6, "сталь сакуры": 4},
    "Пламенный Танто": {"драконья чешуя": 3, "кровавый кристалл": 1},
    #Небесный Странник
    "Посох Ветров": {"перо феникса": 3, "гибкий бамбук": 4},
    "Лук Небесного Пути": {"серебряная нить": 2, "рисовые волокна": 5},
    #Земляной Страж
    "Молот Горы": {"метеоритное железо": 4, "камень горы": 3},
    "Клевец Корней": {"дерево": 5, "смола": 2},
    #Морской Властитель
    "Трезубец Нептуна": {"жемчужина акулы": 2, "коралл": 4},
    "Якорь Глубин": {"цепь из чистого серебра": 3, "электрический кристалл": 1},
    #Призрачный Воин
    "Коса Онрё": {"призрачная ткань": 3, "лунный камень": 2},
    "Веер Забвения": {"сломанный оберег": 2, "воск": 3},
    #Элитное оружие
    "Крылья Гнева": {"слеза гнева": 5, "металл": 10, "несуществуящая материя": 2}
}

armor_recipes = {
    "Ламеллярный нагрудник": {"железо": 4, "шелк": 2},
    "Шлем-кабуто": {"металл": 3, "лакированная древесина": 1},
    "Щит с драконом": {"дерево": 2, "краска": 3},
    "Кираса из стали": {"дамасская сталь": 5, "кожа": 3},
    "Наручи с шелком": {"сталь": 2, "шелк": 4},
    "Поножи с узорами": {"железо": 3, "серебряная нить": 2},
    "Манжеты с чешуей": {"драконья чешуя": 4, "сталь": 2},
    "Плащ из рисовой бумаги": {"рисовые волокна": 6, "воск": 2},
    "Сабатоны": {"железо": 3, "шипы": 4},
    "Маска Они": {"обсидиан": 2, "перья": 3},
    "Наплечники с драконами": {"золото": 1, "сталь": 3},
    "Пояс самурая": {"кожа": 2, "серебро": 1},
    "Кольчуга": {"стальные кольца": 200, "шелк": 1},
    "Перчатки": {"металл": 3, "кожа": 2},
    "Набедренник": {"железо": 4, "золотая фольга": 2},
    #Самурай Рассвета
    "Шлем Рассвета": {"дамасская сталь": 3, "золотая фольга": 2},
    "Доспех Рассвета": {"дамасская сталь": 5, "шелк": 3},
    "Поножи Рассвета": {"дамасская сталь": 4, "кожа": 2},
    #Теневой Странни
    "Маска Теней": {"зачарованная сталь": 2, "пергамент": 3},
    "Мантия Теней": {"ночной шелк": 4, "чернила тэнгу": 2},
    "Сапоги Теней": {"зачарованная сталь": 3, "кожа": 2},
    #Драконий Кузнец
    "Рога Дракона": {"драконья чешуя": 4, "обсидиан": 2},
    "Чешуя Дракона": {"драконья чешуя": 6, "сталь сакуры": 3},
    "Хвост Дракона": {"драконья чешуя": 5, "шипы": 4},
    #Небесный Странник
    "Диадема Ветров": {"перо феникса": 2, "серебряная нить": 3},
    "Одеяние Небес": {"рисовые волокна": 5, "перья": 4},
    "Крылатые Гетры": {"шелковая тетива": 3, "гибкий бамбук": 4},
    #Земляной Страж
    "Шлем Валуна": {"метеоритное железо": 3, "камень горы": 4},
    "Нагрудник Глины": {"лакированная древесина": 5, "глина": 3},
    "Сабатоны Корней": {"дерево": 4, "смола": 2},
    #Морской Властитель
    "Корона Приливов": {"жемчужина акулы": 1, "коралл": 3},
    "Кираса Волн": {"цепь из чистого серебра": 2, "ткань тайфуна": 4},
    "Наголенники Глубин": {"электрический кристалл": 2, "ракушки": 5},
    #Призрачный Воин
    "Маска Онрё": {"сломанный оберег": 2, "призрачная ткань": 3},
    "Роба Призрака": {"детская игрушка": 1, "лунный камень": 2},
    "Сандалии Духов": {"рисовые волокна": 4, "воск": 2}
}

potion_recipes = {
    "маленькое зелье здоровья (+15 HP)": {"Лечебный корень": 3, "Красная трава": 2},
    "среднее зелье здоровья (+25 HP)": {"Лечебный корень": 5, "Синяя трава": 3},
    "большое зелье здоровья (+40 HP)": {"Лечебный корень": 10, "Синяя трава": 5, "Красная трава": 5}
}

#Оружие и броня
weapons_data = {
    "короткий меч-вакидзаси":{"min_damage": 5, "max_damage": 7, "weakness": "физический", "dmg_what": "обычная"},
    "длинный клинок катана": {"min_damage": 13, "max_damage": 15, "weakness": "физический", "dmg_what": "обычная"},
    "вакидзаси": {"min_damage": 12, "max_damage": 20, "weakness": "физический", "dmg_what": "обычная"},
    "танто": {"min_damage": 8, "max_damage": 15, "weakness": "физический", "dmg_what": "обычная"},
    "катана": {"min_damage": 18, "max_damage": 28, "weakness": "физический", "dmg_what": "обычная"},
    "нагината": {"min_damage": 15, "max_damage": 30, "weakness": "физический", "dmg_what": "обычная"},
    "лук": {"min_damage": 10, "max_damage": 24, "weakness": "физический", "dmg_what": "обычная"},
    "кусунгобу": {"min_damage": 30, "max_damage": 45, "weakness": "физический", "dmg_what": "обычная"},
    "боевой веер": {"min_damage": 7, "max_damage": 12, "weakness": "физический", "dmg_what": "обычная"},
    "копьё": {"min_damage": 18, "max_damage": 25, "weakness": "физический", "dmg_what": "обычная"},
    "Рассветная Катана": {"min_damage": 28, "max_damage": 40, "weakness": "световой", "dmg_what": "световая"},
    "Солнечный Нагината": {"min_damage": 32, "max_damage": 45, "weakness": "огненный", "dmg_what": "ледяная"},
    "Коготь Тени": {"min_damage": 25, "max_damage": 35, "weakness": "тьма", "dmg_what": "тьма"},
    "Клинок Лунного Света": {"min_damage": 30, "max_damage": 38, "weakness": "световой", "dmg_what": "световая"},
    "Гнев Дракона": {"min_damage": 40, "max_damage": 55, "weakness": "электрический", "dmg_what": "электрическая"},
    "Пламенный Танто": {"min_damage": 35, "max_damage": 42, "weakness": "огненный", "dmg_what": "ледяная"},
    "Посох Ветров": {"min_damage": 28, "max_damage": 37, "weakness": "ветреной", "dmg_whta":"ветреная"},
    "Лук Небесного Пути": {"min_damage": 33, "max_damage": 44, "weakness": "световой", "dmg_what": "световая"},
    "Молот Горы": {"min_damage": 45, "max_damage": 60, "weakness": "физический", "dmg_what": "обычная"},
    "Клевец Корней": {"min_damage": 38, "max_damage": 48, "weakness": "физический", "dmg_what": "обычная"},
    "Трезубец Нептуна": {"min_damage": 42, "max_damage": 53, "weakness": "водяной", "dmg_what": "огненная"},
    "Якорь Глубин": {"min_damage": 50, "max_damage": 65, "weakness": "физический", "dmg_what": "обычная"},
    "Коса Онрё": {"min_damage": 37, "max_damage": 49, "weakness": "забвение", "dmg_what": "любая"},
    "Веер Забвения": {"min_damage": 30, "max_damage": 40, "weakness": "забвение", "dmg_what": "любая"},
    "Крылья Гнева": {"min_damage": 50, "max_damage": 74, "weakness": "забвение", "dmg_what": "любая"}
}
'''
физический - обычная
огненный - ледяная
световой - световая
тьма - тьма
забвение - любая
ветреной - ветреная
электрический - электрическая
водяной - огненная
'''

armor_data = {
    "Ламеллярный нагрудник": {"defense": 8, "tip": "body"},
    "Шлем-кабуто": {"defense": 6, "tip": "head"},
    "Кираса из стали": {"defense": 12, "tip": "body"},
    "Наручи с шелком": {"defense": 5, "tip": "body"},
    "Поножи с узорами": {"defense": 7, "tip": "legs"},
    "Манжеты с чешуей": {"defense": 9, "tip": "body"},
    "Плащ из рисовой бумаги": {"defense": 4, "tip": "body"},
    "Сабатоны": {"defense": 6, "tip": "legs"},
    "Маска Они": {"defense": 5, "tip": "head"},
    "Наплечники с драконами": {"defense": 8, "tip": "body"},
    "Пояс самурая": {"defense": 3, "tip": "body"},
    "Кольчуга": {"defense": 10, "tip": "body"},
    "Перчатки": {"defense": 4, "tip": "body"},
    "Набедренник": {"defense": 7, "tip": "legs"},
    "Шлем Рассвета": {"defense": 10, "tip": "head"},
    "Доспех Рассвета": {"defense": 18, "tip": "body"},
    "Поножи Рассвета": {"defense": 12, "tip": "legs"},
    "Маска Теней": {"defense": 7, "tip": "head"},
    "Мантия Теней": {"defense": 15, "tip": "body"},
    "Сапоги Теней": {"defense": 9, "tip": "legs"},
    "Рога Дракона": {"defense": 11, "tip": "head"},
    "Чешуя Дракона": {"defense": 20, "tip": "body"},
    "Хвост Дракона": {"defense": 14, "tip": "legs"},
    "Диадема Ветров": {"defense": 6, "tip": "head"},
    "Одеяние Небес": {"defense": 12, "tip": "body"},
    "Крылатые Гетры": {"defense": 8, "tip": "legs"},
    "Шлем Валуна": {"defense": 13, "tip": "head"},
    "Нагрудник Глины": {"defense": 16, "tip": "body"},
    "Сабатоны Корней": {"defense": 11, "tip": "legs"},
    "Корона Приливов": {"defense": 9, "tip": "head"},
    "Кираса Волн": {"defense": 14, "tip": "body"},
    "Наuоленники Глубин": {"defense": 10, "tip": "legs"},
    "Маска Онрё": {"defense": 8, "tip": "head"},
    "Роба Призрака": {"defense": 13, "tip": "body"},
    "Сандалии Духов": {"defense": 7, "tip": "legs"}
}


locations = {
    "Улица Красных Фонарей":{
        "description":
        "Узкая улочка, освещенная сотнями алых бумажных фонарей.\nЗдесь расположены 'изакая' — японские пабы, где самураи и торговцы пьют саке после тяжелого дня.\nВ воздухе смешиваются запахи жареного тофу, копченого угря и древесного угля.\nСлышны звуки сямисена и смех из-за раздвижных дверей.",
        "connections": {
        "выход": "Рынок Двух Ликов"
        },
        "actions": ["зайти_в_изакая", "заснуть ⚠", "задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
    "stamina_cos": 1
    },
    "Бездна": {
    "description": "Загадочное подземелье, которое забрало жизни многих воинов.\nРядом со стеной пещеры вы видите скелет с доспехами и щитом...",
    "connections": {"вернуться": "Заброшенные Шахты"},
    "actions": ["сразиться_с_монстром", "исследовать_развилку", "двигаться_дальше", "Заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки"],
    "stamina_cos": 3
    },
    "Дом": {
        "description": "Ваш уютный дом...",
        "connections": {"выйти": "Рынок Двух Ликов"},
        "actions": ["спать", "осмотреть_комнаты", "сохраниться","задания", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 1
    },
    #Начальная локация
    "Хpам Двух Лун": {
        "description": "Древний храм над крышей которого, ночью можно увидеть пару алых лун.\nА в Хайдэне всегда можно помолиться богам удачи.",
        "connections":{
        },
        "actions": ["тренировка", "сохраниться", "задания", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 0
    },
    #Для квеста
    "Бамбуковый лес": {
        "description": "Густая роща, где стволы бамбука образуют природный лабиринт.\nВ воздухе порхают светлячки-ками, а вдали слышен шепот духов.\nДаже днем, здесь темно, как ночью",
        "connections": {"запад": "Хpам Двух Лун"},
        "actions": ["следовать_за_светлячками", "сохраниться","задания", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 0
    },
    #Обычная локация
    "Храм Двух Лун": {
        "description": 
            "Древний храм над крышей которого, ночью можно увидеть пару алых лун.\n"
            "А в Хайдэне всегда можно помолиться богам удачи.",
        "connections": {
            "север": "Гора Амацу", 
            "восток": "Бамбуковый Лес",
            "запад": "Рыбацкая Деревня",
            "юг": "Сад Лунных Водопадов"
        },
        "actions": ["отправиться_в_Хайдэн", "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 1
    },

    "Бамбуковый Лес": {
        "description":"Густая роща, где стволы бамбука образуют природный лабиринт.\nВ воздухе порхают светлячки-ками, а вдали слышен шепот духов.\nДаже днем, здесь темно, как ночью",
        "connections": {"запад": "Храм Двух Лун"},
        "actions": ["собирать_травы", "следовать_за_светлячками", "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 3
    },
    "Сад Лунных Водопадов": {
        "description": 
            "Террасы с водопадами, струящимися как лунный свет.\n" 
            "Каменные мосты ведут к павильонам, где на воде плавают лепестки сакуры.\n"
            "В центре сада — древний колокол, покрытый мхом.",
        "connections": {
            "север": "Храм Двух Лун", 
            "юг": "Рисовые Поля"
        },
        "actions": ["ударить_в_колокол", "найти_источник_водопада", "сразиться_с_духом_воды", "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 4
    },

    "Заброшенные Шахты": {
        "description": 
            "Тёмные тоннели, где когда-то добывали обсидиан.\n" 
            "Стены покрыты кровавыми надписями, а в глубине слышен плач призрака шахтёра.",
        "connections": {"наверх": "Рисовые Поля", "глубже": "Логово Кайто"},
        "actions": ["битва", "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 2
    },

    "Гора Амацу": {
        "description": 
            "Священная гора, где небо касается земли.\n" 
            "На вершине — алтарь с вечным огнём.",
        "connections": {"юг": "Храм Двух Лун"},
        "actions": ["заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 4
    },

    "Рыбацкая Деревня": {
        "description": 
            "Деревянные дома на сваях над бирюзовой водой.\n" 
            "Рыбаки чинят сети, а на причале танцуют чайки с глазами-бусинами.",
        "connections": {"восток": "Храм Двух Лун", "юг": "Порт Алой Луны"},
        "actions": [ "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 2
    },

    "Логово Кайто": {
        "description": 
            "Чёрная пагода, парящая над пропастью.\n" 
            "Стены исписаны проклятиями, а у входа стоят статуи демонов-хранителей.",
        "connections": {"наверх": "Заброшенные Шахты"},
        "actions": ["заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 5
    },

    "Чайный Дом": {
        "description": 
            "Уютное здание с бумажными фонарями.\n" 
            "Кицунэ в человеческом облике подают матчу, а в углу шепчутся ниндзя.",
        "connections": {"запад": "Рисовые Поля"},
        "actions": ["заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 2
    },

    "Рисовые Поля": {
        "description": 
            "Бескрайние террасы, залитые водой.\n" 
            "Местные фермеры в соломенных шляпах гоняются за призрачными онрё.",
        "connections": {"юг": "Заброшенные Шахты", "восток": "Чайный Дом", "север": "Сад Лунных Водопадов"},
        "actions": ["заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 1
    },

    "Порт Алой Луны": {
        "description": 
            "Шумные доки, где джонки с алыми парусами разгружают бочки саке и шёлк.\n"
            "На причале стоят европейские торговцы в кимоно, а в воздухе витает запах моря и жареных кальмаров.\n"
            "У дальнего пирса покачивается загадочный корабль с чёрными парусами.",
        "connections": {
            "север": "Рыбацкая Деревня",
            "запад": "Рынок Двух Ликов",
        },
        "actions": ["нанять_корабельщика","заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 1
    },
    "Рынок Двух Ликов": {
        "description": 
            "Шумная торговая площадь, разделенная на две части: слева торгуют сталью и доспехами,\n"
            "справа — шелками и чаем. Над головами развеваются флаги с символами кланов.\n"
            "В центре площади стоит аукционный дом с табличкой 'Продажа земли'.",
        "connections": {
            "восток": "Порт Алой Луны",
            "север": "Улица Красных Фонарей"
        },
        "actions": ["купить_дом", "отправиться_в_кузницу", "торговаться", "заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 1  
    },

    "Остров Павших Звезд": {
        "description": 
            "Затерянный остров с каменными статуями в форме созвездий.\n"
            "На песке видны следы крабо, а в пещерах светятся синие кристаллы.",
        "connections": {"вернуться": "Порт Алой Луны"},
        "actions": ["заснуть ⚠","задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
        "stamina_cos": 3
    }
    }

# Сюжетные квесты используют те же меню локаций, что и существующие действия.
# Недостающие точки добавляются как обычные локации, поэтому для них не нужен
# отдельный режим или специальное меню.
def ensure_story_locations():
    story_locations = {
        "Деревня Ниндзя": {
            "description": "Скрытая деревня в чаще леса; здесь Томоэ и её разведчики готовятся к войне.",
            "connections": {"юг": "Бамбуковый Лес"},
            "actions": ["задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
            "stamina_cos": 3,
        },
        "Кузница Драконьей Стали": {
            "description": "Жаркая кузница Гэна у подножия вулкана. Здесь рождается оружие против Бездны.",
            "connections": {"запад": "Рынок Двух Ликов"},
            "actions": ["задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
            "stamina_cos": 3,
        },
        "Пагода Кайто": {
            "description": "Чёрная пагода над разломом. Наверху ждёт последняя дуэль с Кайто.",
            "connections": {"вниз": "Логово Кайто"},
            "actions": ["задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
            "stamina_cos": 4,
        },
        "Врата Теней": {
            "description": "Две луны отражаются в расколотом Зеркале Амацу. Здесь решается судьба миров.",
            "connections": {"назад": "Пагода Кайто"},
            "actions": ["задания", "сохраниться", "инвентарь", "настройки", "выйти_в_меню"],
            "stamina_cos": 2,
        },
    }
    for name, data in story_locations.items():
        locations.setdefault(name, data)
    locations["Бамбуковый Лес"]["connections"].setdefault("север", "Деревня Ниндзя")
    locations["Рынок Двух Ликов"]["connections"].setdefault("кузница дракона", "Кузница Драконьей Стали")
    locations["Логово Кайто"]["connections"].setdefault("пагода", "Пагода Кайто")
    locations["Пагода Кайто"]["connections"].setdefault("врата", "Врата Теней")


def story_action_id(quest_name, stage_name):
    return f"story:{quest_name}:{stage_name}"


def story_action_label(action):
    data = STORY_ACTIONS.get(action)
    return data["hint"] if data else action.replace("_", " ")


def update_quest_availability():
    """Open quests whose prerequisites are complete without changing their state."""
    for quest in quests.values():
        if not quest["started"] and not quest["completed"]:
            quest["available"] = all(quests[name]["completed"] for name in quest["requires"])


def add_story_stage_action(quest_name, stage_name):
    ensure_story_locations()
    stage = quests[quest_name]["stages"][stage_name]
    action = story_action_id(quest_name, stage_name)
    STORY_ACTIONS[action] = {"quest": quest_name, "stage": stage_name, "hint": stage["hint"]}
    actions = locations[stage["location"]]["actions"]
    if action not in actions:
        actions.insert(0, action)


def start_quest(quest_name):
    update_quest_availability()
    quest = quests[quest_name]
    if not quest["available"] or quest["completed"]:
        return False
    quest["started"] = True
    for stage_name, stage in quest["stages"].items():
        if not stage["completed"]:
            stage["started"] = True
            add_story_stage_action(quest_name, stage_name)
            return True
    return False


def advance_story_stage(quest_name, stage_name):
    """Complete the active stage, reveal the next one, and pay quest rewards."""
    quest = quests[quest_name]
    stage = quest["stages"][stage_name]
    action = story_action_id(quest_name, stage_name)
    actions = locations.get(stage["location"], {}).get("actions", [])
    if action in actions:
        actions.remove(action)
    stage["started"] = False
    stage["completed"] = True

    for next_name, next_stage in quest["stages"].items():
        if not next_stage["completed"]:
            next_stage["started"] = True
            add_story_stage_action(quest_name, next_name)
            return False

    quest["completed"] = True
    quest["started"] = False
    player["money"] += quest["reward"].get("gold", 0)
    player["xp"] += quest["reward"].get("xp", 0)
    level_up()
    update_quest_availability()
    return True


def restore_active_quest_actions():
    """Recreate location actions for stages that were active when a save was made."""
    ensure_story_locations()
    for quest_name, quest in quests.items():
        if not quest.get("started", False) or quest.get("completed", False):
            continue
        for stage_name, stage in quest["stages"].items():
            if stage.get("started", False) and not stage.get("completed", False):
                add_story_stage_action(quest_name, stage_name)
                break


#дом
def check_house():
    global player
    if player["house_day"] and not player["house_available"]:
        if game_time.days >= player["house_day"] + 2:
            player["house_available"] = True
            locations["Рынок Двух Ликов"]["connections"]["в лес"] = "Дом"
            print("\nГонец: 'Ваш дом готов! Пройдите по тропинке от рынка!'")



#медленый текст
def slow_print(text, delay=None):
    if delay is None:
        delay = music["text_speed"]
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()
#убрать строку
def ubrat_stroku():
    print("\033[F\033[K", end='')
#начальный диалог
def beginning():
    global player, current_location
    player ["name"] = "Неизвестный"
    while True:
        if music["SFX"]:
            play_sound_with_tag("sound/keyboard.ogg", "key", volume = 0.2)
        time.sleep(0.5)
        slow_print("Япония", 0.2)
        time.sleep(0.5)
        slow_print("Токио", 0.2)
        time.sleep(0.5)
        slow_print("2:31 AM", 0.1)
        time.sleep(0.3)
        clear()
        if music["SFX"]:
            stop_sound_by_tag("key", stop = 400)
        time.sleep(1)
        if music["SFX"]:
            play_sound_with_tag("sound/city.ogg", "key", lop = -1, volume = 0.1 )
            play_sound_with_tag("sound/sain_city.ogg", "rain", lop = -1, volume = 0.2 )
        slow_print("Свет экранов и неоновых вывесок отражается в стеклянных фасадах высоток." )
        if music["SFX"]:
            play_sound_with_tag("sound/game_cont.ogg", "con", lop = -1, volume = music["VOLUME_SFX"])
        slow_print("В комнате, заваленной коллекционными фигурками и коробками от игр, "
            "вы сидите перед монитором, погруженный в игру" )
        print()
        slow_print("\"Как же я устал... Ну ладно, еще немного и спать.\" — пробормотали вы про себя, проворачивая в руках геймпад." )
        dial()
        slow_print("Эта ночь была неспокойная - за окном громыхала гроза." )
        slow_print("Вдруг вы нажимаете на кнопку атаки, и тут же вспышка молнии осветила комнату, а вместе с ней..." )
        if music["SFX"]:
            stop_sound_by_tag("con", stop = 2000)
            stop_sound_by_tag("key", stop = 2000)
            stop_sound_by_tag("rain", stop = 2000)
        time.sleep(2)
        print()
        if music["SFX"]:
            play_sound_with_tag("sound/Flash.ogg", "flash", volume = music["VOLUME_SFX"] )
        slow_print("Темнота." )
        if music["SFX"]:
            stop_sound_by_tag("flash", stop= 1000)
        dial()
        clear()
        if music["music"] and  not a["begin"]:
            if music["VOLUME_MUSIC"] > 0.6:
                play_sound_with_tag("music/begin.ogg", "begin", lop=-1, volume=0.5 )
                a["begin"]=True
            else:
                play_sound_with_tag("music/begin.ogg", "begin", lop=-1, volume=music["VOLUME_MUSIC"])
                a["begin"]=True
        quests ["Пробуждение в Храме"]["started"] = True
        quests ["Пробуждение в Храме"]["stages"]["dialog"]["started"] = True
        slow_print("Вы приходите в себя под шелест бамбука." )
        slow_print("Звук геймпада сменился шелестом татами. Резкий запах ладана ударил в нос." )
        slow_print("Вы пытаетесь встать, но вместо кресла ощущаете под собой циновку." )
        slow_print("Вы: А!? Что за..! Где ноут?.." )
        dial()
        clear()
        slow_print("Вы: Где я?..." )
        slow_print("Сквозь бумажную перегородку пробивается свет алой луны, рисуя на полу узор в виде хризантемы." )
        dial()
        slow_print("Раздвижная дверь с изображением журавля плавно открывается." )
        slow_print("На пороге стоит женщина в шелковом кимоно цветом, схожим с цветом луны, и с веером в руках из рисовой бумаги." )
        slow_print("В её волосах блестит серебряная заколка в форме полумесяца." )
        dial()
        clear()
        slow_print("Незнакомка: Проснись, путник между мирами. Твой сон длился три восхода солнца." )
        slow_print("Её голос звучит одновременно мягко и властно." )
        while True:
            opt = [
                "А вы кто вообще?",
                "Что здесь происходит",
                "Осмотреться молча"
            ]
            choice = handle_menu(opt)
            if choice == -1:
                continue
            if choice == 0:
                clear()
                slow_print("Она раскрывает веер с изображением горы, похожей на гору Фудзи." )
                slow_print("Аяме: Меня зовут Аяме-химэ. Я хранительница этого места." )
                slow_print("Здесь время течет иначе, а грани между мирами тонки." )
                dial()
            elif choice == 1:
                clear()
                slow_print("Она касается рукояти своего меча с красной тесьмой." )
                slow_print("Аяме: Я Аяме-химэ, а ты перешел границу миров в час, когда занавесь между ними истончилась." )
                dial()
            elif choice == 2:
                clear()
                slow_print("Вы замечаете:" )
                slow_print("На стене висит пара мечей в черных ножнах." )
                slow_print("На низком столике — чайный набор и свиток с каллиграфией." )
                slow_print("Аяме: Меня зовут Аяме-химэ. Этот храм — мост между эпохами. Чувствуешь ли ты дыхание прошлого?" )
                dial()
            break
        slow_print("Аяме протягивает вам два меча в лакированных ножнах." )
        slow_print("Аяме: Ты в Землях Двух Лун. Здесь правят законы самураев, забытые в твоём мире." )
        slow_print("Но священные печати разрушены, и тени прошлого угрожают равновесию." )
        while True:
            opt = [
                "И что же от меня требуется?",
                "А я вообще почему?",
                "Взять мечи без слов"
            ]
            choice = handle_menu(opt)
            if choice == -1:
                continue
            if choice == 0:
                a["dialog"]=True
                clear()
                slow_print("Аямэ: До недавних пор, в нашем мире обитали только два вида сущностей: люди и Китцуне." )
                slow_print("То, что ты сейчас видишь - это мой человеческий облик." )
                slow_print('Я не отношусь к рассе людей, я - "Правительница Китцуне".' )
                slow_print("Внезапно, демоны вырвались из ада и смогли нарушить покой в нашем мире." )
                slow_print("Что повлияло и на ваш мир тоже." )
                dial()
                slow_print("Аяме: Тебе следует победить Кайто - здешний демон, который нарушил эту тонкую связь между нашими мирами." )
                slow_print("Но для этого тебе следует обрести силу полубога, котрую ты сможешь получить, пройдя 100 уровневое подзмелье." )
                slow_print("Только ты сможешь сделать это." )
                slow_print("Когда-то наши предки смогли избавить эту змелю от нечести, но теперь я надеюсь, что это сделаешь ты...")
                slow_print("Вы осторожно берете мечи в руки и осматриваете их")
                dial()
            elif choice == 1:
                clear()
                slow_print("Аяме: В тебе есть искра тех, кто когда-то охранял эти земли." )
                slow_print("Ты — последний мост между нашими мирами. Только за тобой будущее наших миров" )
                slow_print("Вы осторожно берете мечи в руки и осматриваете их")
                dial()
            elif choice == 2:
                clear()
                player["inventory"].extend(["короткий меч-вакидзаси", "длинный клинок катана"])
                slow_print("(Получено: пара самурайских мечей!)" )
                slow_print("Аяме: Мудро. Катаной защищай слабых, вакидзаси — храни свою честь." )
                dial()
            break
        clear()

        clear()
        slow_print("Аяме: Ты очень слаб, поэтому тебе следует тренироваться." )
        slow_print("Она проводит веером по воздуху, открывая вид:" )
        slow_print("- Пятиярусная пагода, окруженная вишневым садом" )
        slow_print("- Улицы с деревянными домами, где торговцы предлагают шелк и сталь" )
        slow_print("- Воины в бамбуковых доспехах, отрабатывающие боевые стойки" )
        dial()
        clear()
        if a["dialog"] == True:
            player ["name"] = name_creation()
            slow_print(f"Аяме: Пусть имя {player["name"]} станет легендой, о которой поют у придорожных алтарей." )
            slow_print("Помни — даже в мире теней есть место чести... пока бьется твое сердце." )
            slow_print("Когда ты станешь силнее, то принеси в наши мир спокойстивие." )
            if a["begin"]:
                stop_sound_by_tag("begin", stop=1500)
                a["begin"]=False
                quests ["Пробуждение в Храме"]["stages"]["dialog"]["completed"] = True
                break
            break
        if a["dialog"] == True:

            break
        if not player["bad_ending"] and not a["dialog"]:
            clear()
            slow_print("Аямэ: До недавних пор, в нашем мире обитали только два вида сущностей: люди и Китцуне." )
            slow_print("То, что ты сейчас видишь - это мой человеческий облик." )
            slow_print('Я не отношусь к рассе людей, я - "Правительница Китцуне".' )
            slow_print("Внезапно, демоны вырвались из ада и смогли нарушить покой в нашем мире." )
            slow_print("Что повлияло и на ваш мир тоже." )
            dial()
            slow_print("Аяме: Тебе следует победить Кайто - здешний демон, который нарушил эту тонкую связь между нашими мирами." )
            slow_print("Но для этого тебе следует обрести силу полубога, котрую ты сможешь получить, пройдя 100 уровневое подзмелье." )
            slow_print("Только ты сможешь сделать это." )
            slow_print("Когда-то наши предки смогли избавить эту землю от нечести, но теперь я надеюсь, что это сделаешь ты..." )
            dial()
            player["name"] = name_creation()
            slow_print(f"Аяме: Пусть имя {player["name"]} станет легендой, о которой поют у придорожных алтарей." )
            slow_print("Помни — даже в мире теней есть место чести... пока бьется твое сердце." )
            slow_print("Когда ты станешь силнее, то принеси в наши мир спокойстивие." )
            quests ["Пробуждение в Храме"]["stages"]["dialog"]["completed"] = True
            if a["begin"]:
                stop_sound_by_tag("begin", stop=1500)
                a["begin"]=False
            clear()
        current_location = "Храм Двух Лун"
        if "короткий меч-вакидзаси" in player["inventory"]:
            continue
        else:
            player["inventory"].extend(["короткий меч-вакидзаси", "длинный клинок катана"])
        break

#Выбор снаряги
def equip_menu():
    while True:
        clear()
        print("\n=== Экипировка ===")
        print(f"Оружие: {player['equipped_weapon'] or 'Нет'}")
        print(f"Голова: {player['head'] or 'Нет'}")
        print(f"Тело: {player['body'] or 'Нет'}")
        print(f"Ноги: {player['legs'] or 'Нет'}")
        
        opt = [
            "Сменить оружие",
            "Сменить броню",
            "Назад"
        ]
        choice = handle_menu(opt)
        if choice == -1:
            continue
        if choice == 0:
            change_weapon()
        elif choice == 1:
            change_armor()
            
        elif choice == 2:
            break

#смена оружия
def change_weapon():
    global player
    available_weapons = [item for item in player["inventory"] if item in weapons_data]
    if not available_weapons:
        print("У вас нет оружия в инвентаре!")
        input("Нажмите Enter...")
        return  
    while True:
        clear()
        print("\n=== Выбор оружия ===")
        options = available_weapons.copy()
        options.append("Назад")
        choice = handle_menu(options)
        if choice == -1:
            continue
        if choice == len(options) - 1:
            break
        selected_weapon = available_weapons[choice]
        if player["equipped_weapon"]:
            player["inventory"].append(player["equipped_weapon"])
        player["equipped_weapon"] = selected_weapon
        player["inventory"].remove(selected_weapon)
        print(f"Экипировано: {selected_weapon}!")
        input("Нажмите Enter...")
        break

#смена брони
def change_armor():
    while True:
        clear()
        print("\n=== Выбор брони ===")
        opt = [
            "Голова",
            "Тело", 
            "Ноги",
            "Назад"
        ]
        choice = handle_menu(opt)
        if choice == -1:
            continue
        if choice == 3:
            break
        slots = {
            0: ("head", "Голова"),
            1: ("body", "Тело"), 
            2: ("legs", "Ноги")
        }
        sl, sln = slots[choice]
        change_armor_slot(sl, sln)

def change_armor_slot(slot_key, slot_name):
    global player
    available_armor = []
    for item in player["inventory"]:
        if item in armor_data and armor_data[item]["tip"] == slot_key:
            available_armor.append(item)
    if not available_armor and not player[slot_key]:
        print(f"Нет брони для слота {slot_name}!")
        input("Нажмите Enter...")
        return
    while True:
        clear()
        print(f"\n=== Броня для {slot_name} ===")
        options = []
        if player[slot_key]:
            options.append(f"Снять: {player[slot_key]}")
        for armor in available_armor:
            options.append(armor)
        options.append("Назад")
        choice = handle_menu(options)
        if choice == -1:
            continue
        if choice == len(options) - 1:
            break
        selected_option = options[choice]
        if selected_option.startswith("Снять:"):
            removed_armor = player[slot_key]
            player["inventory"].append(removed_armor)
            player[slot_key] = None
            print(f"Снята броня: {removed_armor}!")
            update_total_defense()
            input("Нажмите Enter...")
            break
        else:
            selected_armor = selected_option
            if player[slot_key]:
                player["inventory"].append(player[slot_key])
            player[slot_key] = selected_armor
            player["inventory"].remove(selected_armor)
            print(f"Экипировано: {selected_armor}!")
            update_total_defense()
            input("Нажмите Enter...")
            break
#Уровень
def level_up():
    global player
    while player["xp"] >= player["xp_tn"]:
        player["xp"] -= player["xp_tn"]
        player["level"] += 1  
        player["xp_tn"] = int(player["xp_tn"] * 1.5)
        player["max_hp"] += 20
        player["hp"] = player["max_hp"]
        player["max_stamina"] += 5
        print(f"Вы повысили уровень! Теперь уровень: {player['level']}, Макс. HP: {player['max_hp']}, Макс. Стамина: {player["max_stamina"]}")
        clear()

# Сохранение данных
def save_game(slot):
    global player
    save_data = {
        "player": player,
        "game_time": game_time.todic(),
        "current_location": current_location,
        "locations": locations,
        "quests": quests
    }
    save_path = os.path.join(SAVE_DIR, f"save_data_{slot}.json")
    try:
        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False)
        print(f"Игра сохранена в слот {slot}")
    except Exception as e:
        print(f"Ошибка сохранения: {str(e)}")
    input("Нажмите Enter, чтобы продолжить")
    clear()
    
    
#Лес
def forest():
    global player
    print("\n=== Сбор трав ===")
    item_chance = random.randint(1,3)
    items = ["Красная трава", "Синяя трава", "Лечебный корень"]
    print(f"Вы нашли {items[item_chance-1]}!")
    player["stamina"] -= 5
    player["inventory"].append(items[item_chance-1])
    game_time.time_up(15)
    input("Нажмите Enter...")


#показ статов
def show_stats():
    global player
    print("\n=== Статистика персонажа ===")

#ДЛЯ РАЗРАБОТКИ, УБРАТЬ НА РЕЛИЗЕ
    print(f"Имя: {player['name']}")
#########################################################
    print(f"Уровень: {player['level']}")
    print(f"Опыт: {player['xp']} / {player['xp_tn']}")
    print(f"Здоровье:  \033[1;31m{player['hp']}\033[0m")
    print(f"Деньги: \033[1;33m{player['money']}\033[0m золота")
    print(f"Стамина: \033[1;34m{player['stamina']}/{player['max_stamina']}\033[0m")
    if player['head'] or player['body'] or player['legs']:
        print("\n--- Экипированная броня ---")
        print(f"Голова: {player['head'] or 'Нет'}")
        print(f"Тело: {player['body'] or 'Нет'}")
        print(f"Ноги: {player['legs'] or 'Нет'}")
        print(f"\nОбщая защита: {player["total_defense"]} ед.")
    else:
        print("Брони нет.")
    print()
    print(f" ===Игровое время: {game_time.gtime()} ({game_time.gdate()})===")
    print()
    while True:
        opt = [
            "Выбрать снаряжение",
            "Инвентарь",
            "Выход"
        ]
        ant = handle_menu(opt)
        if ant == -1:
            continue
        if ant == 0:
            clear()
            equip_menu()
            clear()
            break
        elif ant ==1:
            clear()
            view_items()
            clear()
            show_stats()
            clear()
            break
        elif ant == 2:
            break
    return
#Загрузка сохранения
def load_game(slot):
    global player, game_time, current_location, locations, chanels_for_music, a, quests
    save_path = os.path.join(SAVE_DIR, f"save_data_{slot}.json")
    try:
        with open(save_path, "r", encoding='utf-8') as f:
            save_data = json.load(f)
            player = save_data["player"]
            quests = merge_loaded_quests(save_data.get("quests", {}))
            for field, default_value in DEFAULT_PLAYER.items():
                if field not in player:
                    player[field] = default_value.copy() if isinstance(default_value, (dict, list)) else default_value
            game_time_data = save_data["game_time"]
            current_location = save_data.get("current_location", "Храм Двух Лун")
            locations = save_data.get("locations", locations)
            game_time = GameTime(
                years=game_time_data.get("years", 1),
                months=game_time_data.get("months", 6),
                days=game_time_data.get("days", 1),
                hours=game_time_data.get("hours", 5),
                minutes=game_time_data.get("minutes", 0)
            )
            restore_active_quest_actions()
            update_quest_availability()
        print(f"Игра загружена из слота {slot}")
    except FileNotFoundError:
        print("Сохранение не найдено.")
        input("Введите Enter...")
        clear()
        return
    except Exception as e:
        print(f"Ошибка загрузки: {str(e)}")
        input("Нажмите Enter, чтобы продолжить")
        clear()
        return
    input("Нажмите Enter, чтобы продолжить")
    clear()
    if a["main"]:
        stop_sound_by_tag("main_menu", stop = 1500)
        a["main"] = False
    loading_screen(dlitelnost=3, message="Загрузка...")
    location_menu()
# Очистка экрана
def clear():
    os.system("cls" if os.name == "nt" else "clear")
def get_total_defense():
    global player
    total = 0
    for slot in ["head", "body", "legs"]:
        item = player[slot]
        if item in armor_data:
            total += armor_data[item]["defense"]
    return total
def update_total_defense():
    player["total_defense"] = get_total_defense()
#бой
def battle(enemy=None):
    global player, a, music
    stop_sound_by_tag("locat", 2000)
    stop_sound_by_tag("abyss", 2000)
    if music["music"] and not a["battle"]:
        play_sound_with_tag("music/battle_them.ogg", "battle", -1, music["VOLUME_MUSIC"])
        a["battle"] = True
    if isinstance(enemy, list):
        enemy = random.choice(enemy)
    if not enemy:
        enemy = random.choice(enemies)
    if player["stamina"] < 20:
        print("◈ Вы слишком устали для битвы!")
        input("Нажмите Enter...")
        return False
    enemy_hp = enemy["hp"]
    base_dmg = (5, 10)
    weapon = weapons_data.get(player.get("equipped_weapon", ""), {})
    min_dmg = weapon.get("min_damage", base_dmg[0])
    max_dmg = weapon.get("max_damage", base_dmg[1])
    print(f"\n Битва с {enemy['name']} (HP: {enemy_hp})!")
    input("Нажмите Enter...")
    while enemy_hp > 0 and player["hp"] > 0:
        clear()
        stop_sound_by_tag("locat", 2000)
        stop_sound_by_tag("abyss", 2000)
        if music["music"] and not a["battle"]:
            play_sound_with_tag("music/battle_them.ogg", "battle", -1, music["VOLUME_MUSIC"])
        a["battle"] = True
        print(" === Битва ===")
        armor_def = sum(armor_data.get(item, {}).get("defense", 0) for item in [player["head"], player["body"], player["legs"]])
        print(f"\n Ваше HP: {player['hp']} | Стамина: {player['stamina']}/{player['max_stamina']}")
        print(f" {enemy['name']}: {enemy_hp} HP")
        action = handle_menu(["Атаковать", "Навык", "Сбежать"], "Ваш выбор:")
        if action == 0:
            player["stamina"] = max(0, player["stamina"] - 1)
            damage = random.randint(min_dmg, max_dmg)
            if player.get("blocking", False):
                damage = int(damage * 1.2)
                player["blocking"] = False
            
            enemy_hp = max(0, enemy_hp - damage)
            print(f" Вы нанесли {damage} урона!")  
        elif action == 1:
            if player["skills_act"]:
                skill = handle_menu(
                    [f"Мощный удар (-30 стамины, урон x1.5)", 
                    f"Блок (-15 стамины, снижает урон на 50%)",
                    "Назад"], 
                    "Выберите навык:")
                if skill == 0 and player["stamina"] >= 30:
                    player["stamina"] -= 30
                    damage = int(random.randint(min_dmg, max_dmg) * 1.5)
                    enemy_hp = max(0, enemy_hp - damage)
                    print(f" Критический удар! {damage} урона!")
                elif skill == 1 and player["stamina"] >= 15:
                    player["stamina"] -= 15
                    player["blocking"] = True
                    print(" Вы готовы блокировать следующую атаку!")
                elif skill == 2:
                    continue
            else:
                print("Я еще ничего не знаю...")
                input("Нажмите Enter...")
                continue
        elif action == 2:
            if player["you_can_run"]:
                print(" Вы решаете сбежать...")
                game_time.time_up(10)
                stop_sound_by_tag("battle", 2000)
                a["battle"] = False
                return False
            else:
                print("Нельзя бежать!")
                input("Нажмите Enter...")
                continue
        if enemy_hp > 0:
            enemy_dmg = random.randint(*enemy["damage"])
            if player.get("blocking", False):
                enemy_dmg = int(enemy_dmg * 0.5)
                player["blocking"] = False
                print(" Вы заблокировали часть урона!")
                
            fdmg = max(0, enemy_dmg - armor_def)
            player["hp"] = max(0, player["hp"] - fdmg)
            print(f" {enemy['name']} наносит {fdmg} урона! (Заблокировано: {enemy_dmg - fdmg})")
        if player["hp"] <= 0:
            clear()
            stop_sound_by_tag("battle", 2000)
            a["battle"] = False
            slow_print("Не в силах больше сражаться, вы падаете на землю...")
            print("\n Не все могут быть героями...")
            input("Нажмите Enter...")
            main_menu()
            return False
    loot = random.choice(enemy["loot"])
    gold = random.randint(*enemy["gold"])
    xp_gain = enemy["hp"] // 3
    clear()
    print(f"\n {enemy['name']} побежден!")
    print(f"Получено: {loot}, {gold} золота, {xp_gain} опыта!")
    player["inventory"].append(loot)
    player["money"] += gold
    player["xp"] += xp_gain
    level_up()
    game_time.time_up(20)
    stop_sound_by_tag("battle", 2000)
    a["battle"] = False
    input("Нажмите Enter...")
    return True

#бой с боссом
def battle_with_boss(boss):
    global player
    print(f"\n=== БОСС: {boss['name'].upper()} ===")
    slow_print(f"\n{boss['name']}: {boss['dialog']}")
    boss_hp = boss["hp"]
    special_attack_cooldown = 3
    while player["hp"] > 0 and boss_hp > 0:
        clear()
        print(f"=== {boss['name']} ===")
        print(f"HP врага: {boss_hp}\nВаш HP: {player['hp']} | Стамина: {player['stamina']}/{player['max_stamina']}")
        if random.randint(1, 5) == 1 and special_attack_cooldown <= 0:
            print(f"\n☠ {boss['name']} использует {boss['special_attack']}!")
            damage = int(sum(boss['damage']))
            player["hp"] = max(0, player["hp"] - damage)
            print(f"Вам нанесено {damage} урона!")
            special_attack_cooldown = 3
            input("\nНажмите Enter...")
            continue
        else:
            special_attack_cooldown -= 1
        options = ["Атаковать", "Навыки", "Бежать"]
        action = handle_menu(options)
        if action == 0:
            weapon = weapons_data.get(player["equipped_weapon"], {"min_damage": 10, "max_damage": 20})
            damage = random.randint(weapon["min_damage"], weapon["max_damage"])
            if player.get("blocking", False):
                damage = int(damage * 0.5)
                player["blocking"] = False
            boss_hp = max(0, boss_hp - damage)
            print(f"Вы нанесли {damage} урона!")
            input("\nНажмите Enter...")
            if boss_hp > 0:
                enemy_damage = random.randint(*boss["damage"])
                armor_def = sum(armor_data.get(item, {}).get("defense", 0) for item in [player["head"], player["body"], player["legs"]])
                dealt_damage = max(0, enemy_damage - armor_def)
                player["hp"] = max(0, player["hp"] - dealt_damage)
                print(f"{boss['name']} наносит вам {dealt_damage} урона! (Заблокировано: {enemy_damage - dealt_damage})")
        elif action == 1:
            skill = handle_menu(["Мощный удар (-30 стамины)", "Блок (-15 стамины)"], "Выберите навык:")
            if skill == 0 and player["stamina"] >= 30:
                weapon = weapons_data.get(player["equipped_weapon"], {"max_damage": 20})
                damage = int(weapon["max_damage"] * 1.5)
                boss_hp = max(0, boss_hp - damage)
                player["stamina"] -= 30
                print(f"Критический удар! {damage} урона!")

            elif skill == 1 and player["stamina"] >= 15:
                player["blocking"] = True
                player["stamina"] -= 15
                print("Вы готовы блокировать следующую атаку!")
            input("\nНажмите Enter...")
        elif action == 2:
            print("Вы сбежали от босса!")
            game_time.time_up(20)
            return False
        if player["hp"] <= 0:
            print("Вы пали в бою...")
            main_menu()
            return False
    if boss_hp <= 0:
        print(f"\n★ {boss['name']} повержен! ★")
        player["abyss_kills"] += 1
        if "abyss_floor" in player:
            player["abyss_floor"] += 1
        loot = random.choice(boss["loot"])
        gold = random.randint(*boss["gold"])
        player["inventory"].append(loot)
        player["money"] += gold
        player["xp"] += boss["hp"]
        
        level_up()
        game_time.time_up(60)
        input("\nНажмите Enter...")
        return True
        
            
# Крафт
def craft(item_type):
    if player["stamina"] < 30:
        print("Я слишком устал...")
        input("Нажмите Enter...")
        return
    recipes = weapon_recipes if item_type == "weapon" else armor_recipes
    print(f"\n=== Крафт {'оружия' if item_type == 'weapon' else 'брони'} ===")
    available_recipes = []
    for item, materials in recipes.items():
        can_craft = True
        for mat, qty in materials.items():
            if player["inventory"].count(mat) < qty:
                can_craft = False
                break
        if can_craft:
            available_recipes.append(item)
    if not available_recipes:
        print("Нет доступных рецептов!")
        input("Нажмите Enter...")
        return
    for i, item in enumerate(available_recipes, 1):
        print(f"{i}. {item}: {recipes[item]}")
    try:
        choice = int(input("Выберите номер предмета (0 для отмены): "))
        if choice == 0:
            return
        selected_item = available_recipes[choice-1]
        recipe = recipes[selected_item]
        for mat, qty in recipe.items():
            if player["inventory"].count(mat) < qty:
                print(f"Не хватает {mat}!")
                input("Нажмите Enter...")
                return
        for mat, qty in recipe.items():
            for _ in range(qty):
                player["inventory"].remove(mat)
        if item_type == "weapon":
            player["inventory"].append(selected_item)
        else:
            player["inventory"].append(selected_item)
        print(f"Успешно создано: {selected_item}!")
        game_time.time_up(30)
        input("Нажмите Enter...")
        return
    except (ValueError, IndexError):
        print("Неверный выбор!")
        input("Нажмите Enter...")
# Магазин
def shop():
    global player
    items = {
        "дамасская сталь": 200,
        "шелк": 150,
        "зачарованная сталь": 500,
        "перья": 75,"лакированная древесина":120,
        "железо": 50, 
        "кожа": 25, 
        "металл": 100, 
        "порох": 150, 
        "ткань": 30, 
        "драконья чешуя": 300, 
        "рисовые волокна": 120, 
        "краска": 80, 
        "серебряная нить": 150, 
        "золотая фольга": 250, 
        "стальные кольца": 1,
        "серебряный слиток": 180,
        "железо": 50,
        "шелк": 150,
        "бамбук": 30,
        "рисовые волокна": 80,
        "дамасская сталь": 200,
        "сталь сакуры": 350,
        "лунный камень": 400,
        "обсидиан": 220,
        "золотая фольга": 280,
        "серебряная нить": 170,
        "метеоритное железо": 600,
        "перо феникса": 1200,
        "кровавый кристалл": 900,
        "электрический кристалл": 750,
        "жемчужина акулы": 800,
        "свиток чести": 1000,
        "цепь из чистого серебра": 450,
        "солнечный сплав": 700,
        "ночной шелк": 300,
        "ткань тайфуна": 550,
        "чернила тэнгу": 480,
        "гибкий бамбук": 80,
        "шелковая тетива": 120,
        "лакированная древесина": 150,
        "бронза": 100,
        "шипы": 40,
        "серебро": 200,
        "пергамент": 60,
        "воск": 70
        }
    while True:
        print(f"\n=== Магазин ===\nВаши деньги: {player['money']} монет")
        for i, (item, price) in enumerate(items.items(), 1):
            print(f"{i}. {item} - {price} монет")
        print("0. Выйти")

        choice = input("> ")
        if choice == "0":
            clear()
            break
        try:
            choice = int(choice)
            item_name = list(items.keys())[choice - 1]
            price = items[item_name]

            if player["money"] >= price:
                player["money"] -= price
                player["inventory"].append(item_name)
                print(f"Вы купили {item_name}")
                game_time.time_up(5)
                input("Нажмите Enter, чтобы выйти.")
                clear()
            else:
                print("Недостаточно денег!")
        except (IndexError, ValueError):
            print("Неверный выбор!")
            input("Нажмите Enter...")
            clear()

#читы
def cheat_menu():
    global player
    while True:
        clear()
        print("\n=== ЧИТ-МЕНЮ ===")
        print("1. Изменить максимальное HP")
        print("2. Восстановить HP")
        print("3. Добавить предметы")
        print("4. Добавить оружие")
        print("5. Добавить броню")
        print("6. Увеличить XP")
        print("7. Добавить денег")
        print("8. Установить уровень")
        print("9. Полное восстановление")
        print("0. Выйти")
        
        choice = input("> ")
        
        if choice == "1":
            new_hp = int(input("Новое максимальное HP: "))
            player["max_hp"] = new_hp
            player["hp"] = new_hp
            print(f"Макс. HP установлено: {new_hp}")
            
        elif choice == "2":
            player["hp"] = player["max_hp"]
            print("HP полностью восстановлено!")
            
        elif choice == "3":
            item = input("Введите название предмета: ")
            qty = int(input("Количество: "))
            player["inventory"].extend([item]*qty)
            print(f"Добавлено {qty}x {item}")
            
        elif choice == "4":
            print("Доступное оружие:")
            for weapon in weapons_data:
                print(f"- {weapon}")
            weapon = input("Введите название оружия: ")
            if weapon in weapons_data:
                player["inventory"].append(weapon)
                print(f"Добавлено: {weapon}!")
            else:
                print("Такого оружия нет!")
                
        elif choice == "5":
            print("Доступная броня:")
            for armor in armor_data:
                print(f"- {armor}")
            armor = input("Введите название брони: ")
            if armor in armor_data:
                player["inventory"].append(armor)
                print(f"Добавлено: {armor}!")
            else:
                print("Такой брони нет!")
                
        elif choice == "6":
            xp = int(input("XP для добавления: "))
            player["xp"] += xp
            level_up()
            print(f"Добавлено {xp} XP!")
            
        elif choice == "7":
            amount = int(input("Сумма: "))
            player["money"] += amount
            print(f"Добавлено {amount} золота!")
            
        elif choice == "8":
            new_level = int(input("Новый уровень: "))
            player["level"] = new_level
            player["xp_tn"] = 50 * (1.5 ** (new_level-1))
            print(f"Установлен уровень {new_level}!")
            
        elif choice == "9":
            player["hp"] = player["max_hp"]
            player["stamina"] = player["max_stamina"]
            player["illness"] = False
            player["heat"] = False
            print("Полное восстановление!")
            
        elif choice == "0":
            clear()
            break
            
        input("\nНажмите Enter...")
        clear()
        return
#локации
def location_menu():
    global current_location, player, a
    current_index = 0
    while True:
        clear()
        if current_location == "Бездна" and music["music"]:
            stop_sound_by_tag("locat", stop=1000)
            a["location"] = False
            if not a["abyss"]:
                play_sound_with_tag("music/abyss.ogg", "abyss", lop=-1, volume=music["VOLUME_MUSIC"])
                a["abyss"] = True
        if not current_location =="Бездна":
            stop_sound_by_tag("abyss", 1000)
            a["abyss"] = False
            if music["music"] and a["location"] == False:
                wfjjwojf = random.randint(1,2)
                time_for_music=game_time.hours
                if time_for_music > 6 and time_for_music < 16:
                    if wfjjwojf == 1:
                        play_sound_with_tag("music/locat.ogg", "locat", lop = -1, volume = music["VOLUME_MUSIC"])
                        a["location"] = True
                    else:
                        play_sound_with_tag("music/locat_2.ogg", "locat",lop = -1, volume = music["VOLUME_MUSIC"])
                        a["location"] = True
                else:
                    if wfjjwojf == 1:
                        play_sound_with_tag("music/locat_night.ogg", "locat", lop = -1, volume = music["VOLUME_MUSIC"])
                        a["location"] = True
                    else:
                        play_sound_with_tag("music/locat_night_2.ogg", "locat",lop = -1, volume = music["VOLUME_MUSIC"])
                        a["location"] = True     
        clear()
        loc = locations[current_location]
        time_str = f"◈ Время: {game_time.gtime()} {game_time.gdate()} ◇ Стамина: {player['stamina']}/{player['max_stamina']} ◈"
        border = '═' * (len(time_str) + 10)
        print(f"{border}")
        print(f" {time_str} ")
        print(f"{border}\n")
        if current_location == "Бездна":
            if player["abyss_floor"] < 10:
                print(f"╔{'═'*(len(current_location)+12)}╗")
                print(f"║ {current_location.upper()}: {player["abyss_floor"]} ЭТАЖ   ║")
                print(f"╚{'═'*(len(current_location)+12)}╝")
            if player["abyss_floor"] > 9 and player["abyss_floor"] < 100:
                print(f"╔{'═'*(len(current_location)+12)}╗")
                print(f"║ {current_location.upper()}: {player["abyss_floor"]} ЭТАЖ  ║")
                print(f"╚{'═'*(len(current_location)+12)}╝")
            if player["abyss_floor"] == 100:
                print(f"╔{'═'*(len(current_location)+12)}╗")
                print(f"║ {current_location.upper()}: {player["abyss_floor"]} ЭТАЖ ║")
                print(f"╚{'═'*(len(current_location)+12)}╝")
        else:
            print(f"╔{'═'*(len(current_location)+4)}╗")
            print(f"║ {current_location.upper()}   ║")
            print(f"╚{'═'*(len(current_location)+4)}╝")
        print(loc["description"])

        loc = locations[current_location]
        connections = list(loc["connections"].items())
        actions = loc["actions"]
        
        print("\n▷ Пути:")
        if loc["connections"]:
            connections = list(loc["connections"].items())
            for i, (direction, target) in enumerate(connections):
                pref = " > " if i == current_index else "  "
                print(f" │{pref}[{direction.upper()}] → {target}")
        else:
            print(" × Путей нет...")
        print("\n◉ Действия:")
        act = loc["actions"]
        k = 1
        for i, action in enumerate(act, start=len(connections)):
            pref = " > " if i == current_index else "  "
            krch = str(k)
            print(f" │{pref}{krch}. {story_action_label(action)}")
            k += 1
        k = 1
        key = get_key()
        max_index = (len(connections) + len(actions)) - 1 if connections else len(actions) - 1
        if key == b'w':
            current_index = (current_index - 1) % (max_index + 1)
        elif key == b's':
            current_index = (current_index + 1) % (max_index + 1)
        elif key == b'\r':
            if connections:
                if current_index < len(connections):
                    direction, target = connections[current_index]
                    st_cost = locations[target].get("stamina_cos", 5)
                    if player["stamina"] >= st_cost:
                        player["stamina"] -= st_cost
                        current_location = target
                        game_time.time_up(20)
                        print()
                        loading_screen(2, "Перемещение")
                    else:
                        print("Недостаточно стамины!")
                        input("Нажмите Enter...")
                else:
                    action_index = current_index - len(connections)
                    handle_location_action(actions[action_index])
            else:
                if current_index < len(actions):
                    handle_location_action(actions[current_index])
            current_index = 0

#Отправка на другой остров
def ship_going():
    global current_location
    if player["money"] >= 150 and player["stamina"] >= 30:
        player["money"] -= 150
        player["stamina"] -= 15
        current_location = "Остров Павших Звезд"
        print("Капитан корабля: 'Добро пожаловать на борт! Плывём через море теней...'")
        game_time.time_up(80)
    else:
        print("Капитан корабля: 'Эй, земляк, 150 золота - или ищи другой корабль!'")
        input("Нажмите Enter...")
        game_time.time_up(10)
        clear()
        return
    
#Экстренный сон
def sleep_with_danger():
    global player
    if player["stamina"] < 20:
        if player["money"] > 150:
            stolen = int(player["money"] * 0.02)
            player["money"] -= stolen
        player["stamina"] = min(player["stamina"] + 70, player["max_stamina"])
        print(f"⚠ Вы уснули, но проснулись без {stolen} золота!")
        print(f"Стамина восстановлена до {player['stamina']}.")
        game_time.time_up(120)
    else:
        print("Сейчас спать нельзя, дурень!")
        input("Нажмите Enter...")
        return

#Колокол для атаки
def kolokol():
    global player
    if player["stamina"] >= 15:
        player["stamina"] -= 15
        player["temp"] = 1.2

        slow_print("Вы ударяете по колоколу, и его гул разносится по всей округе." )
        input("Нажмите Enter...")
        game_time.time_up(10)
    else:
        slow_print("Слишком устал, чтобы поднять молот..." )
        input("Нажмите Enter...")

#источник
def istochnik():
    global player
    if player["stamina"] >= 20:
        player["stamina"] -= 20
        roll = random.random()
        if roll <= 0.05:
            loot = random.choice(["Лунный жемчуг", "Серебряный цветок"])
            player["inventory"].append(loot)
            print(f"✦ В струях воды вы нашли {loot}!")
        else:
            print("Источник скрыт туманом...")
            game_time.time_up(30)
            input("Нажмите Enter...")
#диалог для молитвы для плохой концовки
def plohoy_dialog_hram():
    while True:
        if a["location"]:
            stop_sound_by_tag("locat", stop= 2000)
            a["location"]= False
        slow_print("Вы заходите в Хайдэн, который был очень уж похож на тот, что был в вашем мире." )
        slow_print("Вы никогда в своей жизни не бывали в таких местах, не верущий ведь." )
        dial()
        if music["SFX"]:
            play_sound_with_tag("sound/pol.ogg", "pol", lop = -1, volume = music["VOLUME_SFX"])
        slow_print("Ступени звонко хрустят под ногами. В воздухе висит запах ладана и... крови?" )
        slow_print("Вы: Почему тут странно пахнет?" )
        time.sleep(1)
        slow_print("Вдруг вы замечате странное движение рядом с вами." )
        if music["SFX"]:
            stop_sound_by_tag("pol", stop=2000)
        dial()
        slow_print("В этот момент, сзади ящика с подношениями, вылетает непонятное черное облако, похожое на призрака. " )
        slow_print("И тут же улетает к потолку." )
        dial()
        slow_print("Черное пятно: Шшшш! Проваливай от сюда Предатель!" )
        time.sleep(1)
        slow_print("Прошипел призрак." )
        slow_print("Вы: Никуда я не пойду!" )
        
        dial()
        slow_print("Но призрака уже не было, когда вы сказали свои слова." )
        slow_print("Вы: Странный какой... Ну ладно, пора молиться!" )
        dial()
        break

#Хорший диалог храм
def horoshiy_dialog_hram():
    while True:
        if a["location"]:
            stop_sound_by_tag("locat", stop= 2000)
            a["location"]= False
        slow_print("Вы заходите в Хайдэн, который был очень уж похож на тот, что был в вашем мире." )
        slow_print("Вы никогда в своей жизни не бывали в таких местах, не верущий ведь." )
        dial()
        slow_print("Вы замечаете Аямэ около ящика для подношений." )
        slow_print("Мысли: Китцуне тоже моляться здешним богам удачи?" )
        slow_print("Мысли: Нужно подойти к ней и спросить обо всем." )
        dial()
        if music["SFX"]:
            play_sound_with_tag("sound/pol.ogg", "pol", lop = -1, volume = music["VOLUME_SFX"])
        slow_print("Вы медленно подходите к Аямэ." )
        time.sleep(2)
        if music["SFX"]:
            stop_sound_by_tag("pol", stop=2000)
        slow_print("Аямэ: Пришел помолиться?" )
        slow_print("Не смотря на то, что пол под вами скрипел, было не удивительно, что Аямэ вас услышала." )
        slow_print("Но внезапный вопрос все равно смутил вас, от чего вы немного растерялись." )
        slow_print("Вы: А?... Да... Возможно..." )
        dial()
        slow_print("Аямэ: Хорошо, тогда не буду мешать." )
        slow_print("Она медленно поварачивается к вам." )
        slow_print("На ее лице вы замечаете приятную улыбку, которая согревает вашу душу." )
        dial()
        slow_print("Когда же она ушла из вашего вида, вы захотели будто бы что-то ей сказать." )
        slow_print("Но когда вы повернулись в ее сторону, то ее уже не было..." )
        slow_print("Вы: Ого, быстро же она. Наверное в ее обычный облик превратилась..." )
        dial()
        slow_print("Мысли: Ну ладно, это сейчас не важно. Приступиим к тому, зачем я сюда пришел..." )
        break



    
    
#прекрафкт
def precraft():
    global player
    if not player["bad_ending"]:
        slow_print("Кузнец: Добро пожаловать! Хотели бы что-то выковать?" )
        option = [
            "Выковать оружие",
            "Выковать броню"
        ]
        while True:
            inta = handle_menu(option)
            if inta == 0:
                clear()
                craft("weapon")
                return
            elif inta == 1:
                clear()
                craft("armor")
                return

#молитва
def molitva():
    global player, game_time
    if a["location"]:
        stop_sound_by_tag("locat", stop=2000)
        a["location"]= False
    loading_screen(dlitelnost=2, message="Подходим")
    if player["pervaya_molitva"] == True:
        if player["bad_ending"] == True:
            if not a["hram"] and music["music"]:
                play_sound_with_tag("music/hram.ogg", "hram", lop=-1, volume=music["VOLUME_MUSIC"])
                a["hram"] = True
            plohoy_dialog_hram()
            player["pervaya_molitva"] = False
        else:
            if not a["hram"] and music["music"]:
                play_sound_with_tag("music/hram.ogg", "hram", lop=-1, volume=music["VOLUME_MUSIC"])
                a["hram"] = True
            horoshiy_dialog_hram()
            
            player["pervaya_molitva"] = False
    clear()
#神様、助けてください！！！！！！！！！！！！！！
#やめてえええええ！えええええ！
    while True:
        if not a["hram"] and music["music"]:
            play_sound_with_tag("music/hram.ogg", "hram", lop=-1, volume=music["VOLUME_MUSIC"])
            a["hram"] = True
        opt = [
            "Взять рис для подношений",
            "Поднести бросить рис в саисенбако",
            "Позвонить в судзу",
            "Совершить поклоны (2-4-1)",
            "Произнести молитву",
            "Выйти"
        ]
        choice = handle_menu(opt, "༄༄༄༄ Хайден ༄༄༄༄")
        if player["stamina"] > 10:
            if choice == -1:
                continue
            if choice == 0:
                print("༄ Вы взяли рис для подношей...")
                input("Нажмите Enter...")
                clear()
                player["inventory"].append("рис")
            elif choice == 1:
                if "рис" in player["inventory"]:
                    print("༄ Вы слишите, как рис падает на дно ящика...")
                    input("Нажмите Enter...")
                    clear()
                    player["inventory"].remove("рис")
                else:
                    print("༄ нужно сначала взять рис...")
                    input("Нажмите Enter...")
                    clear()
            elif choice == 2:
                if music["SFX"]:
                    play_sound_with_tag("sound/bell.ogg", "bell", volume=music["VOLUME_SFX"])
                print("༄ Слышен тихий звон колокольчика...")
                input("Нажмите Enter...")
                clear()
            elif choice == 3:
                if music["SFX"]:
                    play_sound_with_tag("sound/clap.ogg", "clap", lop=1, volume=music["VOLUME_SFX"])
                print("༄ Вы совершаете поклоны: 2 хлопка, 4 поклона, 1 молитва...")
                input("Нажмите Enter...")
                clear()
            elif choice == 4:
                print("༄ Вы: Ками-сама, даруй силу, чтобы победить демона Кайто...")
                input("Нажмите Enter...")
                clear()
                player["hp"] = player["max_hp"]
            player["stamina"] -= 2
            if choice == 5:
                clear()
                stop_sound_by_tag("hram", stop = 2000)
                a["hram"] = False
                loading_screen(dlitelnost=2, message="Уходим")
                player["stamina"] -= 1
                break
        else:
            print("༄ Я слишком устал...")
            input("Нажмите Enter...")
            clear()
        
#битва с боссами
def boss_batle():
    global player
    boss = None
    if player["abyss_floor"] == 30:
        boss = {
            "name": "Тень Предательства",
            "hp": 300,
            "damage": (40, 55),
            "loot": ["кольцо скорби"],
            "gold": (150, 200),
            "special_attack": "Клинок Судьбы",
            "dialog": "Вы слышите крики погибших воинов..."
        }
    if player["abyss_floor"] == 65:
        boss = {
            "name": "Глаз Бездны",
            "hp": 600,
            "damage": (60, 85),
            "loot": ["око прозренья"],
            "gold": (300, 400),
            "special_attack": "Смертный Приговор",
            "dialog": "Неразборчиво: Т*во~ см~~ть №!*! з~есь**!"
        }
    if boss is None:
        return False
    return battle_with_boss(boss)
    #if player["hp"] > 0:
        
"""
def finnal_abyss_batle():
    global player
    final = {
            "name": "Хранитель Бездны",
            "hp": 1000,
            "damage": (70, 90),
            "loot": ["сердце жизни"],
            "gold": (1000, 5000),
            "special_attack": "Смертный Приговор",
            "dialog": "Вы слышите только оглушительный крик..."
        }
    battle(final, boss=True)
    if player["hp"] > 0:
        slow_print("")
"""
def training():
    global quests, locations, current_location, a
    stop_sound_by_tag("locat", 2000)
    a["location"] = False
    quests ["Пробуждение в Храме"]["stages"]["training"]["started"] = True
    slow_print("Вы приближаетесь к соломенному манекену, чья поверхность испещрена следами тысяч клинков." )
    slow_print("Золотистые стебли, перевязанные бамбуковыми обручами, шелестят на ветру." )
    slow_print("Пальцы сжимают рукоять катаны - холодный металл кажется чужим, почти враждебным в неумелых руках." )
    dial()
    slow_print('"Слишком высоко держишь локти" - голос звучит сзади, мягкий, но полный безмолвного авторитета.' )
    slow_print("Обернувшись, вы застываете: Аямэ стоит в луче алого света, её серебряные волосы переливаются" )
    slow_print("Её кимоно с вышитыми хризантемами колышиться от ветра, а глаза светятся рубиновым отблеском." )
    dial()
    slow_print(' "Меч - продолжение души, а не груда металла" - её пальцы скользят по вашим запястьям, выправляя вашу стойку.' )
    slow_print("Прикосновения ледяные, как горный ручей, но в них странная успокаивающая сила." )
    slow_print('"Попробуй понять свой мечь... Вот так" - она поправляет ваш мечь.' )
    dial()
    time.sleep(1)
    slow_print("Аямэ отступает на шаг, закрывая лицо своим веером." )
    slow_print(' "А теперь покажи, как ты обращаешся с клинком" - спокойно сказала она.' )
    dial()
    enemy_hp = 30
    while enemy_hp > 0:
        clear()
        print("=== Тренировка ===")
        print("\n Имя: Манекен, HP: ", enemy_hp)
        ant = handle_menu(["Атаковать <---", "Навык", "Бежать"], "Ваш выбор:")
        if ant == 0:
            clear()
            damage = random.randint(1, 5)
            print("\nВы нанесли: ", damage, " урона!")
            time.sleep(1)
            enemy_hp -= damage
            input("Нажмите Enter...")
        if ant == 1:
            clear()
            print("\nЯ еще ничего не знаю...")
            input("Нажмите Enter...")
        if ant == 2:
            clear()
            print("И зачем мне бежать?..")
            input("Нажмите Enter...")
    clear()
    slow_print("После решающего удара, манекен падает на землю..." )
    slow_print('"Теперь ты наш защитник" - с усмешкой сказала девушка.' )
    slow_print("Вы невольно улыбнулись ей в ответ." )
    dial()
    slow_print('"Теперь ты готов сразиться с настоящим врагом" - сказала она.' )
    slow_print('"Пройди в Бамбуковый Лес, а там следуй за светлячками, они покажут дорогу"' )
    slow_print("Взмахнув веером, она указала вам путь." )
    input("Нажмите Enter...")
    clear()
    quests ["Пробуждение в Храме"]["stages"]["training"]["completed"] = True
    locations["Храм Двух Лун"]["connections"]["восток"] = "Бамбуковый Лес"
    locations["Храм Двух Лун"]["actions"].remove("тренировка")

def folowing():
    global player, current_location,a
    stop_sound_by_tag("locat", 2000)
    a["location"] = False
    quests ["Пробуждение в Храме"]["stages"]["first_battle"]["started"] = True
    slow_print("Прийдя вместе с Аямэ к Бамбуковому Лесу, вы замечаете скопления светлячков-ками." )
    slow_print("Они словно балерины, кружа в небе, вырисовывают красивые узоры в небе." )
    slow_print("Никогда в жизни вы не видили чего-то столь красивого." )
    slow_print("Их движения согревали душу и радовали глаза." )
    dial()
    slow_print("Но через небольшой промежуток времени, светлячки отправились в глубь леса." )
    slow_print('"Вперед, за ними." - сказала девушка рядом с вами.' )
    dial()
    slow_print("Вы идёте по извилистой тропе, где стволы бамбука смыкаются в арки, которые словно ведут в другой мир." )
    slow_print("Легкий ветер оставляет на ваших щеках приятное, прохладное ощущение." )
    slow_print('"Даже не вериться, что здесь может быть кто-то, кто может навредить нам." - произнесли вы смело.' )
    dial()
    slow_print(f'"Внешность обманчива, {player["name"]}" - произнесла девушка.' )
    slow_print("Но даже не успев подумать над ответом, вы видите странную фигуру в метрах так двадцати." )
    dial()
    slow_print("Фигура эта была похожа на девушку в рваном кимоно." )
    slow_print("Ее лицо было скрыто маской ханья, а глаза горели огнем." )
    slow_print("Почуяв что-то не то, вы быстро останавливаетесь, приготовившись к бою." )
    slow_print('"Демон..." - тихо сказала Аямэ.' )
    dial()
    slow_print('"Оставляю ее на тебя, удачи!" - быстро произнесла девушка.' )
    slow_print("Обернувшись, вы замечаете, что девушки уже нет." )
    slow_print('"Лисий облик..." - подумали вы.' )
    dial()
    slow_print('"Ки-и-и! Чужак! Твоя душа станет жертвой Кайто!" - противно произносит демон.' )
    slow_print("В ту же секунду она быстро направляется в вашу сторону, злобно смеясь." )
    oni = {
        "name": "Они-баку", 
        "hp": 40, 
        "damage": (5, 9),
        "loot": ["маска ханья"],
        "gold": (10, 25)
    }
    battle(oni)
    clear()
    if player["hp"] > 0:
        player["you_can_run"] = True
        player["skills_act"] = True
        slow_print("После финального удара катаной, Они-баку падает на землю, не в силах больше сражаться..." )
        slow_print("После него остается только маска, которая была на лице." )
        slow_print("Вы осторожно поднимаете её." )
        dial()
        slow_print("Через какое-то время, в вихре ветра появляется Аямэ." )
        slow_print("Вы обратили на нее внимание." )
        slow_print("Она пыталась перевести дух после битвы со своими противниками." )
        slow_print("На ее лице можно было прочитать страх, который она очень чательно скрывала." )
        slow_print("Красивый веер был испачкан кровью, а на кимоно можно было увидить слегка заметные следы крови.")
        dial()
        slow_print('"Ты сделал это... Но это лишь начало..." - переводя дух, сказала Аямэ' )
        slow_print('"Та маска, что ты подобрал, поможет тебе в будущем. Сохрани её." - сказала девушка' )
        slow_print('"На данный момент ты свободень, можешь иследовать наш мир." - собравшись уходить, сказала Аямэ.')
        slow_print('"Я буду ждать тебя в Чайном Доме через один восход солнца. Пройди от Храма Двух Лун на юг до рисовых полей."' )
        slow_print('"А там уже поверни на восток, тогда и найдешь это место."' )
        slow_print("Вы качнули головой, давая знак, что вы все поняли." )
        dial()
        slow_print("После нескольких секунд, Аямэ уже не было в лесу." )
        slow_print("Остались только вы, вместе с тишиной и звуками светляков.")
        input("Нажмите Enter...")
        awakening = quests["Пробуждение в Храме"]
        awakening["stages"]["first_battle"]["completed"] = True
        awakening["started"] = False
        awakening["completed"] = True
        update_quest_availability()
        current_location = "Бамбуковый Лес"

def visit_izakaya():
    global game_time, player
    while True:
        clear()
        print("╔════════════════════════════════════╗")
        print("║       ИЗАКАЯ 'АЛЫЙ ФОНАРЬ'         ║")
        print("╚════════════════════════════════════╝")
        print(f"Время: {game_time.gtime()} | Ваши деньги: {player['money']} золота")
        print(f"Здоровье: {player['hp']}/{player['max_hp']} | Стамина: {player['stamina']}/{player['max_stamina']}")
        print("\nХозяин: Ирашяймасэ! Что желаете, самурай-сама?")
        options = []
        if game_time.hours >= 21 or game_time.hours <= 6:
            options.append("Переночевать в комнате для гостей (7 часов сна)")
        else:
            options.append("Переночивать (только с 21:00 до 6:00)")
        options.append("Заказать суши и саке (+50 HP, -50 золота)")
        options.append("Поесть рамен (+30 HP, -30 золота)")
        options.append("Выпить зеленого чая (+20 стамины, -20 золота)")
        if game_time.hours >= 18 or game_time.hours <= 24:
            options.append('Сыграть в кости "Чёт-Нечёт"')
        else:
            options.append("Игра в кости (только с 18:00 до 23:59)")
        options.append("Поболтать с хозяином")
        options.append("Выйти из изакая")
        ch = handle_menu(options)
        if ch == -1:
            continue
        if ch == 0:
            if 21 <= game_time.hours or game_time.hours <= 6:
                if player["money"] >= 100:
                    player["money"] -= 100
                    player["stamina"] = player["max_stamina"]
                    player["hp"] = min(player["hp"] + 30, player["max_hp"])
                    game_time.time_up(420)
                    print("\nВы провели ночь в уютной комнате на татами.")
                    print("Стамина полностью восстановлена, здоровье +30.")
                    input("Нажмите Enter...")
                else:
                    print("\nУ вас недостаточно денег! Ночлег стоит 100 золота.")
                    input("Нажмите Enter...")
            else:
                print("\nСейчас слишком рано для ночлега! Приходите после 21:00.")
                input("Нажмите Enter...")
        elif ch == 1:
            if player['money']>=50:
                player["money"]-=50
                player["hp"] = min(player["hp"] + 50, player["max_hp"])
                game_time.time_up(30)
                print("\nВы наслаждаетесь суши и саке.")
                print("Здоровье восстановлено на 50 единиц.")
                input("Нажмите Enter...")
            else:
                print("\nНедостаточно денег! Суши и саке стоят 50 золота.")
                input("Нажмите Enter...")
        elif ch == 2:
            if player["money"] >= 30:
                player["money"] -= 30
                player["hp"] = min(player["hp"] + 30, player["max_hp"])
                game_time.time_up(20)
                print("\nВы съели горячий рамен с курицей и овощами.")
                print("Здоровье восстановлено на 30 единиц.")
                input("Нажмите Enter...")
            else:
                print("\nНедостаточно денег! Рамен стоит 30 золота.")
                input("Нажмите Enter...")
        elif ch==3:
            if player["money"] >= 20:
                player["money"] -= 20
                player["stamina"] = min(player["stamina"] + 20, player["max_stamina"])
                game_time.time_up(15)
                print("\nВы пьете ароматный зеленый чай.")
                print("Стамина восстановлена на 20 единиц.")
                input("Нажмите Enter...")
            else:
                print("\nНедостаточно денег! Чай стоит 20 золота.")
                input("Нажмите Enter...")
        elif ch==4:
            if game_time.hours>= 18 and game_time.hours <= 24:
                play_dice()
            else:
                print("\nИгры начинаются только вечером! Приходите с 18:00 до 23:59.")
                input("Нажмите Enter...")
        elif ch==5:
            if player["stamina"] < 5:
                print("\n Вы слишком устали...")
                input("Нажмите Enter...")
                clear()
            else:
                story_telling()
                clear()
        elif ch==6:
            clear()
            print("\nХозяин: Аригато гозаимасу! Ждем снова!")
            input("Нажмите Enter...")
            break
#Разговоры с владельцем
def story_telling():
    global game_time, player
    clear()
    print("\nХозяин изакая: А, вы новенький? Слышал, вы пришли из другого мира.")
    print("Здесь у нас спокойно, но в последнее время демоны стали беспокоить.")
    
    stories = [
        "Никто не знает, что находиться на сотом этаже бездны...",
        "Аямэ-химэ иногда заходит к нам выпить саке. Красивая, но грустная...",
        "Будьте осторожны в Заброшенных Шахтах. Там водятся призраки шахтеров...",
        "Лучшее саке привозят из деревни у подножия Горы Амацу...",
        "Видели того торговца с черного корабля? Говорят, он продает запрещенные артефакты..."
    ]
    story = random.choice(stories)
    game_time.time_up(60)
    player["stamina"]=player["stamina"] - 10
    print(f"\n{story}")
    input("\nНажмите Enter...")

def play_dice():
    global player, game_time
    while True:
        clear()
        print("╔════════════════════════════════════╗")
        print("║        ИГРА 'ЧЁТ-НЕЧЁТ'            ║")
        print("╚════════════════════════════════════╝")
        print("Правила: бросаем два кубика. Вы угадываете, будет сумма чётной или нечётной.")
        print(f"Ваши деньги: {player['money']} золота")
        if player["money"] <= 0:
            print("\nУ вас нет денег для игры!")
            input("Нажмите Enter...")
            return
        print("\nСделайте ставку (введите сумму):")
        try:
            bet = int(input())
            if bet <= 0:
                print("\nСтавка должна быть больше нуля!")
                input("Нажмите Enter...")
                continue
            if bet > player['money']:
                print('\nУ вас нет столько денег!')
                input("Нажмите Enter...")
                continue
        except ValueError:
            print("\nВвидет число!")
            input("Нажмите Enter...")
            continue
        clear()
        print("\n╔════════════════════════════════════╗")
        print("║        ИГРА 'ЧЁТ-НЕЧЁТ'            ║")
        print("╚════════════════════════════════════╝")
        print("")
        print('\nНа что ставите?')
        options = ["Четное","Нечетное","Передумал"]
        choice = handle_menu(options)
        if choice == 2:
            return
        dice_role1 = random.randint(1,6)
        dice_role2 = random.randint(1,6)
        total = dice_role1 + dice_role2
        even = total % 2 == 0
        print(f"\nБросок! Кости №1: {dice_role1}, Кости №2: {dice_role2}. Сумма: {total}")
        won = False
        won = False
        if choice == 0 and even:
            won = True
        elif choice == 1 and not even:
            won = True
        if won:
            winnings = bet
            player["money"] += winnings
            print(f"Вы выиграли! Получаете {winnings} золота!")
            print(f"Теперь у вас: {player['money']} золота")
        else:
            player["money"] -= bet
            print(f"Вы проиграли {bet} золота.")
            print(f"Теперь у вас: {player['money']} золота")
        game_time.time_up(30)
        print("\nХотите сыграть еще?")
        options = ["Да", "Нет"]
        choice = handle_menu(options)
        if choice == 1 or choice == -1:
            break
        clear()

#действия в локациях
def handle_location_action(action):
    clear()
    global a, current_location, player, locations
    if action in STORY_ACTIONS:
        quest_name = STORY_ACTIONS[action]["quest"]
        stage_name = STORY_ACTIONS[action]["stage"]
        completed = advance_story_stage(quest_name, stage_name)
        if completed:
            print(f"Квест «{quest_name}» завершён!")
        else:
            print("Этап квеста завершён. Новая цель отмечена в меню заданий.")
        input("Нажмите Enter...")
        return
    if current_location == "Порт Алой Луны":
        if action == "нанять_корабельщика":
            ship_going()
    if current_location == "Улица Красных Фонарей" and action=="зайти_в_изакая":
        visit_izakaya()
        return
    if action == "сохраниться":
        save_load_menu('save')
        return
    if current_location == "Храм Двух Лун":
        if action == "отправиться_в_Хайдэн":
            molitva()
    if action == "инвентарь":
        show_stats()
        return
    if action == "отправиться_в_кузницу":
        clear()
        precraft()
        return
    if action == "выйти_в_меню":
        main_menu()
    if action == "заснуть ⚠":
        sleep_with_danger()
        return
    if action == "ударить_в_колокол":
        kolokol()
        return
    if action == "найти_источник_водопада":
        istochnik()
        return
    if action == "настройки":
        if music["music"]:
            stop_sound_by_tag("locat", 2000)
            stop_sound_by_tag("abyss", 2000)
            a["location"] = False
            a["abyss"] = False
        settings()
        return
    if action == "сразиться_с_духом_воды":
        if player["stamina"] >= 20:
            enemy = {
            "name": "Дух Водопада", 
            "hp": 200, 
            "damage": (25, 40), 
            "loot": ["Амулет Потока"], 
            "gold": (200, 300)
            }
            battle(enemy)
        else:
            print("Нет, я слишком устал...")
            input("Нажмите Enter...")
    if action == "спать":
        if game_time.hours >= 21 or game_time.hours <= 6:
            player["stamina"] = player["max_stamina"]
            player["hp"] = player["max_hp"]
            game_time.time_up(480)
            print("Вы хорошо отдохнули!")
        else:
            print("Нужно заняться делом...")
        input("Нажмите Enter...")
    if action == "торговаться":
        shop()
        return
    if action == "задания":
        quest_menu()
        return
    if current_location == "Бамбуковый Лес" and action == "следовать_за_светлячками":
        folowing()
    if action == "купить_дом":
        if not player["house_build"]:
            if player["money"] >= 5000:
                player["money"] -= 5000
                player["house_day"] = game_time.days
                print("Риелтор: 'Стройка займет 2 дня. Ждите нашего гонца!'")                
                player["house_build"] = True
                locations["Рынок Двух Ликов"]["actions"].remove("купить_дом")
            else:
                print("Риелтор: 'Для покупки нужно 5000 золота!'")
                input("Нажмите Enter...")
        else:
            print("Ваш дом скоро будет готов...")
            input("Нажмите Enter...")
            clear()

    if action == "битва":
        battle()
        return
    if action == "тренировка" and not quests ["Пробуждение в Храме"]["stages"]["training"]["started"]:
        training()
        return
    if action == "двигаться_дальше":
        if player["abyss_kills"] >= 2 and player["abyss_floor"] < 100:
            player["abyss_floor"] += 1
            player["abyss_kills"] = 0
            print(f"Вы спустились на {player["abyss_floor"]} этаж...")
            input("Нажмите Enter...")
        if player["abyss_kills"] < 2:
            remaining_kills = 2 - player["abyss_kills"]
            print(f"Нужно убить еще {remaining_kills} монстров.")
            input("Нажмите Enter...")
    if action == "исследовать_пещеры" and not player["abyss_were_found"]:
        if not player["abyss_were_found"]:
            stop_sound_by_tag("locat", 2000)
            a["location"] = False
            slow_print("В надежде найти что-то полезное в этих заброшенных шахтах, вы решаете исследовать их немного." )
            slow_print("Когда-то в этих просторных пещерах добывался обсидиан, который появлялся из-за высокой концентрации маны..." )
            slow_print("Но после появления демона, мана просто исчезла." )
            slow_print("Мысли: Возможно, что эта пещера - это источник силы демона..." )
            dial()
            slow_print("Находясь долгое время без воздуха, вам начинают слышаться звуки рабочих, которые когда-то тут работали." )
            slow_print("Звон кирок, крики рабочих, звуки магии - заполонили ваши уши." )
            slow_print("Казалось, будто все это наяву, не смотря на то, что вокруг пустота." )
            dial()
            slow_print("Но все это - отголоски прошлого, не имеющие ничего общего с реальностью." )
            slow_print("В этот момент, за каменной стеной пещеры, вы замечаете слабое свечение." )
            slow_print("Вы: Хм, что же это может быть? Нужно посмотреть..." )
            dial()
            slow_print("Когда вы добралсиь до источника света, то увидели небольшой кристал, который испускал слабо заметные лучи белого свечения." )
            slow_print("Он словно белая хризантема, указывал на то, что это место скрывает за собой большие тайны..." )
            dial()
            slow_print("Этот кристал не давал вам покоя, будто маня вас." )
            slow_print("Вы решаете дотронуться до него..." )
            dial()
            slow_print("Как только вы коснулись кристала, тот засиял алыми лучами, и все окрасилось в цвет крови..." )
            slow_print("В вас тут же срабатывает рефлекс, и вы закрываете глаза...")
            dial()
            time.sleep(1)
            slow_print("После того, как вы открыли глаза, перед вами снова появился тот самый белый кристал." )
            slow_print("Мысли: И что же это было такое?" )
            dial()
            slow_print("Вы замечаете, что что-то изменилось и тут же оборачиваетесь." )
            slow_print("В ту же секунду, вам открывается вид на громадную пещеру, которая не поддается описанию." )
            slow_print("Она была настолько большая, что тут бы поместился бы целый город." )
            dial()
            if not player["bad_ending"]:
                slow_print("Но вы сразу вспоминаете рассказ Аямэ." )
                slow_print("Для победы, мы должны пройти подземелье, в котором 100 этажей." )
                slow_print("Вы: Похоже это оно и есть..." )
                slow_print("А это значит, что вы уже на шаг впереди." )
                dial()
                print('"Теперь вы можете пройти 100 уровневое подземелье!"')
                input("Нажмите Enter...")
                clear()
            else:
                slow_print("Вы: наверное, это и есть то самое 100 уровневое подземелье." )
                slow_print("Вы: Осталось его только пройти, раз плюнуть!" )
                dial()
                print('"Теперь вы можете пройти 100 уровневое подземелье!"')
                input("Нажмите Enter...")
                clear()
            locations["Заброшенные Шахты"]["actions"].remove("исследовать_пещеры")
            locations["Заброшенные Шахты"]["connections"]["тьма"] = "Бездна"
            current_location = "Бездна"
            player["abyss_were_found"] = True
    if action == "сменить_доспехи":
        equip_menu()
        update_total_defense()
        return
    if current_location == "Бездна":
        if action == "сразиться_с_монстром":
            if player["abyss_floor"] == 30 and player["abyss_kills"] >= 2:
                boss_batle()
                return
            if player["abyss_floor"] == 65 and player["abyss_kills"] >= 2:
                boss_batle()
                return
            if player["abyss_floor"] <= 30:
                enemy = [
                    {"name": "Заяц-Мутант", "hp": 80, "damage": (20, 30), "loot": ["шерсть", "мясо"], "gold": (15, 30)},
                    {"name": "Волк-Мутант", "hp": 85, "damage": (30, 35), "loot": ["пылающий мех",], "gold": (20, 40)},
                    {"name": "Крыса-Мутант", "hp": 80, "damage": (15, 25), "loot": ["мясо"], "gold": (20, 50)},
                ]
            if player["abyss_floor"] > 30 and player["abyss_floor"] <= 65:
                enemy = [
                    {"name": "Змея-Мутант", "hp": 120, "damage": (34, 42), "loot": ["яд тьмы", ], "gold": (55, 90)},
                    {"name": "Громадный Паук", "hp": 130, "damage": (40, 46), "loot": ["шёлк кошмара"], "gold": (45, 75)},
                ]
            if player["abyss_floor"] > 65 and player["abyss_floor"] < 100:
                enemy = [
                    {"name": "Проклятое Око", "hp": 200, "damage": (35, 50), "loot": ["линза света"], "gold": (70, 110)},
                    {"name": "Безглавый", "hp": 170, "damage": (32, 48), "loot": ["тряпьё"], "gold": (65, 100)}
                ]
            if battle(enemy):
                player["abyss_kills"] += 1

    input("Нажмите Enter...")


#Настройки
def settings():
    global player, a,music
    clear()
    stop_sound_by_tag("abyss", 2000)
    stop_sound_by_tag("locat", 2000)
    a["main"] = False
    a["abyss"] = False
    a["location"] = False
    stop_sound_by_tag("main_menu", stop = 1500)
    while True:
        opt = [
            "Настройки громкости",
            "Настройки текста",
            "Выход"
        ]
        inta = handle_menu(opt, "=== Настройки ===")
        if inta == -1:
            continue
        if inta == 0:
            clear()
            while True:
                opt = [
                    "Громкость музыки",
                    "Громкость эффектов",
                    "Включить/Отключить музыку",
                    "Включть/Отключить эффекты",
                    "Выход"
                ]
                pur = handle_menu(opt, "=== Настройки звука ===")
                if pur == -1:
                    continue
                if pur == 0:
                    try:
                        volummusic = float(input("Введите значени(от 0.0 до 1.0): "))
                        if volummusic > 1.0 or volummusic < 0.0 or not float and not int and str:
                            input("Ошибка. Нажмите Enter...")
                            clear()
                        else:
                            music["VOLUME_MUSIC"] = volummusic
                            input("Нажмите Enter...")
                            clear()
                    except:
                        input("Ошибка. Нажмите Enter...")
                        clear()
                elif pur == 1:
                    try:
                        volumsound = float(input("Введите значени(от 0.0 до 1.0): "))
                        if volumsound > 1.0 or volumsound < 0.0 and not float and not int and str:
                            input("Ошибка. Нажмите Enter...")
                            clear()
                        else:
                            music["VOLUME_SFX"] = volumsound
                            input("Нажмите Enter...")
                            clear()
                    except:
                        input("Ошибка. Нажмите Enter...")
                        clear()
                elif pur == 2:
                    if music["music"]:
                        music["music"] = False
                        input("Музыка отключена. Нажмите Enter...")
                        clear()
                    else:
                        music["music"] = True
                        input("Музыка включена. Нажмите Enter...")
                        clear()
                elif pur == 3:
                    if music["SFX"]:
                        music["SFX"] = False
                        input("Эффекты отключены. Нажмите Enter...")
                        clear()
                    else:
                        music["SFX"] = True
                        input("Эффекты включены. Нажмите Enter...")
                        clear()
                elif pur == 4:
                    clear()
                    settings_save()
                    return     
        elif inta == 1:
            clear()
            while True:
                opt = [
                    f"Скорость текста: {music['text_speed']} сек",
                    "Быстрый текст (0.01 сек)",
                    "Средняя скорость (0.05 сек)", 
                    "Медленный текст (0.1 сек)",
                    "Выход"
                ]
                pur = handle_menu(opt, "=== Настройки текста ===")
                if pur == -1:
                    continue
                if pur == 0:
                    try:
                        speed = float(input("Введите скорость (секунды): "))
                        if 0.001 <= speed <= 0.5:
                            music["text_speed"] = speed
                            print(f"Скорость текста установлена: {speed} сек")
                        else:
                            print("Скорость должна быть от 0.001 до 0.5 секунд")
                        input("Нажмите Enter...")
                        clear()
                    except ValueError:
                        input("Ошибка: введите число. Нажмите Enter...")
                        clear()
                elif pur == 1:
                    music["text_speed"] = 0.01
                    print("Установлена быстрая скорость текста")
                    input("Нажмите Enter...")
                    clear()
                elif pur == 2:
                    music["text_speed"] = 0.05
                    print("Установлена средняя скорость текста")
                    input("Нажмите Enter...")
                    clear()
                elif pur == 3:
                    music["text_speed"] = 0.1
                    print("Установлена медленная скорость текста")
                    input("Нажмите Enter...")
                    clear()
                elif pur == 4:
                    clear()
                    settings_save()
                    return
        elif inta == 2:
            clear()
            return
            
def music_on_or_off():
    loading_screen(dlitelnost=3, message="Загружаемся")
    clear()
    music["text_speed"] = 0.05
    while True:
        opt = [
            "Да",
            "Нет"
        ]
        inta = handle_menu(opt, "Хотите ли вы включить музыку?")
        if inta == -1:
            continue
        if inta == 0:
            music["music"] = True
            clear()
            break
        elif inta == 1:
            music["music"] = False
            clear()
            break
    while True:
        inta = handle_menu(opt, "Хотите ли вы включить эффекты?")
        if inta == -1:
            continue
        if inta == 0:
            music["SFX"] = True
            clear()
            break
        elif inta == 1:
            music["SFX"] = False
            clear()
            break



# Главное меню
def main_menu():
    global a, current_location, music
    stop_sound_by_tag("locat", 2000)
    a["location"] = False
    stop_sound_by_tag("abyss", 2000)
    a["abyss"] = False
    while True:
        if not a["main"] and music["music"]:
            play_sound_with_tag("music/main_menu_them.ogg", "main_menu", lop=-1, volume=music["VOLUME_MUSIC"])
            a["main"] = True
        options = [
            "Новая игра",
            "Загрузить игру", 
            "Меню разраба",
            "Настройки",
            "Выйти"
        ]
        choice = handle_menu(options, "===ГЛАВНОЕ МЕНЮ===")
        if choice == -1:
            continue
        clear()
        if choice == 0:
            a["main"] = False
            stop_sound_by_tag("main_menu", stop=2000)
            beginning()
            location_menu()
        elif choice == 1:
            save_load_menu('load')
        elif choice == 2:
            quests ["Пробуждение в Храме"]["started"] = True
            quests ["Пробуждение в Храме"]["stages"]["dialog"]["started"] = True
            quests ["Пробуждение в Храме"]["stages"]["dialog"]["completed"] = True
            stop_sound_by_tag("main_menu", stop=0)
            player["name"] = name_creation()
            current_location = "Храм Двух Лун"
            current_location ="Храм Двух Лун"
            player["inventory"].extend(["короткий меч-вакидзаси", "длинный клинок катана"])
            location_menu()
        elif choice == 3:
            settings()
        elif choice == 4:
            sys.exit()


def show_quest_details(quest_name):
    quest = quests[quest_name]
    while True:
        clear()
        print(f"╔{'═' * (len(quest_name) + 4)}╗")
        print(f"║  {quest_name.upper()}  ║")
        print(f"╚{'═' * (len(quest_name) + 4)}╝")
        status = "Завершено ✓" if quest.get("completed", False) else "В процессе ◯" if quest.get("started", False) else "Доступно ●"
        print(f"Статус: {status}")
        print(f"Описание: {quest['description']}")
        reward = quest.get("reward", {})
        reward_text = []
        if "gold" in reward:
            reward_text.append(f"{reward['gold']} золота")
        if "xp" in reward:
            reward_text.append(f"{reward['xp']} опыта")
        if reward_text:
            print(f"Награда: {', '.join(reward_text)}")
        print("\nЭтапы:")
        stages = quest.get("stages", {})
        for stage_name, stage_data in stages.items():
            status_icon = "✓" if stage_data.get("completed", False) else "◯" if stage_data.get("started", False) else "×"
            print(f"  {status_icon} {stage_data.get('hint', stage_name)}")
        if quest_name == "Песня Трех Источников":
            artifacts = ["Сердце Воды", "Обсидиановый кинжал", "Веер Ветров"]
            collected = []
            if "Сердце Воды" in player["inventory"]:
                collected.append("✓ Сердце Воды")
            else:
                collected.append("◯ Сердце Воды")
            if "Обсидиановый кинжал" in player["inventory"]:
                collected.append("✓ Обсидиановый кинжал")
            else:
                collected.append("◯ Обсидиановый кинжал")
            if "Веер Ветров" in player["inventory"]:
                collected.append("✓ Веер Ветров")
            else:
                collected.append("◯ Веер Ветров")
            print(f"\nАртефакты: {', '.join(collected)}")
        print(f"\nПрогресс: {calculate_quest_progress(quest)}%")
        options = ["Вернуться к списку заданий"]
        if quest.get("available", False) and not quest.get("started", False) and not quest.get("completed", False):
            options.insert(0, "Начать задание")
        choice = handle_menu(options, "Действия:")
        
        if choice == -1:
            continue
            
        if options[choice] == "Начать задание":
            start_quest(quest_name)
            print("Задание начато! Цель добавлена в нужную локацию.")
            input("Нажмите Enter...")
        else:
            break
def calculate_quest_progress(quest):
    if quest.get("completed", False):
        return 100
    stages = quest.get("stages", {})
    if not stages:
        return 0
    completed_stages = sum(1 for stage in stages.values() if stage.get("completed", False))
    total_stages = len(stages)
    return int((completed_stages / total_stages) * 100)
def view_items():
    global player
    cur_page = 0
    i_per_p = 10
    if not player['inventory']:
        print("Инвентарь пуст.")
        input("Нажмите Enter...")
        return
    while True:
        clear()
        print("\n=== Инвентарь ===")
        inv_count = {}
        for item in player['inventory']:
            inv_count[item] = inv_count.get(item, 0) + 1
        list = []
        for item, count in inv_count.items():
            if count > 1:
                list.append(f"{item} x{count}")
            else:
                list.append(item)
        tpages = (len(list) + i_per_p - 1) // i_per_p
        st_ind = cur_page * i_per_p
        e_ind = min(st_ind + i_per_p, len(list))
        for i in range(st_ind, e_ind):
            print(f"{i+1}. {list[i]}")
        print(f"\nСтраница {cur_page + 1}/{tpages}")
        options = []
        if cur_page > 0:
            options.append("Предыдущая страница")
        if cur_page < tpages - 1:
            options.append("Следующая страница")
        options.append("Назад")
        choice = handle_menu(options)
        if choice == -1:
            continue
        if options[choice] == "Предыдущая страница":
            cur_page -= 1
        elif options[choice] == "Следующая страница":
            cur_page += 1
        elif options[choice] == "Назад":
            break
current_quest_page = 0
selected_quest_index = 0
def quest_menu():
    global current_quest_page, selected_quest_index
    update_quest_availability()
    available_quests = []
    for quest_name, quest_data in quests.items():
        if quest_data.get("started", False) or quest_data.get("available", False) or quest_data.get("completed", False):
            available_quests.append(quest_name)
    if not available_quests:
        print("Нет доступных заданий")
        input("Нажмите Enter...")
        clear()
        return
    cur_page = 0
    quests_per_page = 5
    while True:
        clear()
        print("╔════════════════════════════╗")
        print("║         ЗАДАНИЯ           ║")
        print("╚════════════════════════════╝")
        st_ind = cur_page * quests_per_page
        e_ind = st_ind + quests_per_page
        current_quests = available_quests[st_ind:e_ind]
        tpages = (len(available_quests) + quests_per_page - 1) // quests_per_page
        print(f"Страница {cur_page + 1}/{tpages}\n")
        options = []
        for i, quest_name in enumerate(current_quests):
            quest = quests[quest_name]
            status = "✓" if quest.get("completed", False) else "◯" if quest.get("started", False) else "●"
            options.append(f"{status} {quest_name}")
        if cur_page > 0:
            options.append("◀ Предыдущая страница")
        if cur_page < tpages - 1:
            options.append("Следующая страница ▶")
        options.append("Выход")
        current_index = 0
        while True:
            clear()
            print("╔════════════════════════════╗")
            print("║         ЗАДАНИЯ           ║")
            print("╚════════════════════════════╝")
            print(f"Страница {cur_page + 1}/{tpages}\n")
            for i, option in enumerate(options):
                prefix = "  > " if i == current_index else "  "
                print(f"{prefix}{option}")
            print(f"\nУправление: W/S - выбор, A/D - страницы, Enter - выбрать, Esc - назад")
            key = get_key()
            if key == b'w':
                current_index = (current_index - 1) % len(options)
            elif key == b's':
                current_index = (current_index + 1) % len(options)
            elif key == b'a':
                if cur_page > 0:
                    cur_page -= 1
                    break
            elif key == b'd':
                if cur_page < tpages - 1:
                    cur_page += 1
                    break
            elif key == b'\r':
                selected_option = options[current_index]
                if selected_option == "Выход":
                    clear()
                    return
                elif selected_option == "◀ Предыдущая страница":
                    cur_page -= 1
                    break
                elif selected_option == "Следующая страница ▶":
                    cur_page += 1
                    break
                else:
                    quest_name = selected_option[2:]
                    show_quest_details(quest_name)
                    break
            elif key == b'\x1b':
                clear()
                return
def dictionary():
    terms = {
        "Маска ханья": "Хання (яп. 般若) — маска, которая используется в японском театре, представляющая собой страшный оскал ревнивой женщины, демона или змеи.",
        "Ками": "От яп. 神(kami) - Бог",
        "Цукубаи": "Каменная чаша для ритуального очищения перед молитвой",
        "Сайсенбако": "Ящик для подношений монеток в храмах",
        "Судзу": "Веревка с колокольчиком для призыва ками",
        "2-4-1": "Традиционная последовательность поклонов: 2 хлопка, 4 поклона, 1 молитва",
        "Китцуне": "мифическое существо-ёкай в японской мифологии и фольклоре, лисица, обладающая сверхъестественными способностями.",
        "Хайдэн": " зал для молящихся в синтоистском храмовом комплексе",
        "Ладан": "Ароматическая смола, получаемая из трёхвидов деревьев рода Босвеллия",
        "Циновка": "Плетёное полотно, из лыка, соломы, камыша и других материалов",
        "Они": "Японский демон-людоед с рогами, часто вооружён железной палицей",
        "Ронин": "Самурай без господина, странствующий воин-изгой",
        "Бакэмоно": "Сверхъестественные существа в японском фольклоре (общий термин)",
        "Кодама": "Дух дерева, проявляющийся как светящийся шар или гуманоидная фигура",
        "Дзасики-вараси": "Дух ребёнка-пранкера, приносящий удачу, если его уважают",
        "Кайто": "В контексте игры - повелитель демонов (от 海道 - 'морской путь')",
        "Кимун-ками": "Дух-лис (альтернативное название кицунэ)",
        "Вакидзаси": "Короткий меч (30-60 см), носимый в паре с катаной",
        "Танто": "Кинжал самурая (15-30 см) с односторонней заточкой",
        "Катана": "Длинный изогнутый меч (60-80 см) - основной меч самурая", 
        "Нагината": "Алебарда с длинной рукоятью и изогнутым лезвием",
        "Кусунгобу": "Церемониальный меч для сэппуку (длина ~50 см)",
        "Сэппуку": "Харакири",
        "Боевой веер": "Тэссен - складной веер с металлическими спицами, используемый как оружие",
        "Юми": "Японский асимметричный лук (в игре просто 'лук')",
        "Кабуто": "Шлем самурая с характерным козырьком и защитой шеи",
        "До": "Кираса (нагрудник) из металлических пластин",
        "Хайдатэ": "Набедренник в виде разделённого передника",
        "Сунэатэ": "Поножи из металлических полос",
        "Котэ": "Наручи с кольчужной защитой",
        "Мэнгу": "Маска для лица (часто в виде демонической гримасы)",
        "Дамасская сталь": "Узорчатая сталь с высокой твёрдостью и гибкостью",
        "Обсидиан": "Вулканическое стекло, используемое для ритуальных ножей",
        "Шёлковая тетива": "Тетива из особо прочного шёлка-сырца",
        "Драконья чешуя": "В игре - магически упрочнённые чешуйки для брони",
        "Лунный жемчуг": "Мифическая жемчужина, светящаяся в темноте",
        "Сталь сакуры": "Легендарная сталь с розовым оттенком (аналог булата)",
        "Пагода": "Многоярусная буддийская башня-храм",
        "Татами": "Плетёные соломенные маты стандартного размера (ок. 90x180 см)",
        "Сёдзи": "Раздвижные двери с бумажными вставками",
        "Дзэн-сад": "Сад камней для медитации (вероятно, 'Сад Лунных Водопадов')",
        "Тории": "Ритуальные ворота в синтоистских святилищах",
        "Амацу": "Небесный мир в синтоизме (в игре - священная гора)",
        "Сэппуку": "Ритуальное самоубийство самурая через вспарывание живота",
        "Бусидо": "Кодекс чести самурая ('путь воина')",
        "Ками": "Божество или дух в синтоизме",
        "Макото": "Абсолютная искренность - ключевая добродетель самурая",
        "Укиё": "Букв. 'плывущий мир' - эстетика быстротечности жизни",
        "Моно-но аварэ": "Грустное очарование недолговечности вещей",
        "Клевец": "односторонний клювовидный выступ на холодном оружии для нанесения точечного удара"
    }

    cat = {
        "Существа": sorted(["Они", "Ронин", "Бакэмоно", "Кодама", "Дзасики-вараси", "Кайто", "Кимун-ками", "Китцуне", "Ками"]),
        "Оружие": sorted(["Вакидзаси", "Танто", "Катана", "Нагината", "Кусунгобу", "Боевой веер", "Юми", "Клевец"]),
        "Броня": sorted(["Кабуто", "До", "Хайдатэ", "Сунэатэ", "Котэ", "Мэнгу"]),
        "Материалы": sorted(["Дамасская сталь", "Обсидиан", "Шёлковая тетива", "Драконья чешуя", "Лунный жемчуг", "Сталь сакуры", "Ладан"]),
        "Архитектура": sorted(["Пагода", "Татами", "Сёдзи", "Дзэн-сад", "Тории", "Амацу", "Циновка", "Хайдэн", "Сайсенбако","Цукубаи"]),
        "Философия": sorted(["Сэппуку", "Бусидо", "Ками", "Макото", "Укиё", "Моно-но аварэ", "Маска ханья"]),
        "Прочее": sorted(["2-4-1", "Судзу", ])
    }

    print("\n╔════════════════════════════╗")
    print("║    ЯПОНСКИЙ СЛОВАРЬ        ║")
    print("╚════════════════════════════╝")
    
    print("\n\033[1;36m◆ СЛОВАРЬ ИГРЫ ◆\033[0m")
    for term in sorted(terms, key=str.lower):
        print(f"  \033[1m{term}\033[0m: {terms[term]}")

    input("\nНажмите Enter, чтобы вернуться...")
    clear()

def save_load_menu(mode='load'):
    cur_page = 0
    sl_in_pg = 9
    total_slots = 40
    totl_p = (total_slots + sl_in_pg - 1) // sl_in_pg
    while True:
        clear()
        title = "СОХРАНИТЬ ИГРУ" if mode == 'save' else "ЗАГРУЗИТЬ ИГРУ"
        print(f"╔{'═' * (len(title) + 4)}╗")
        print(f"║  {title}  ║")
        print(f"╚{'═' * (len(title) + 4)}╝")
        print(f"Страница {cur_page + 1}/{totl_p}")
        print()
        str_sl = cur_page * sl_in_pg + 1
        end_sl = min((cur_page + 1) * sl_in_pg, total_slots)
        options = []
        for slot in range(str_sl, end_sl + 1):
            save_file = os.path.join(SAVE_DIR, f"save_data_{slot}.json")
            if os.path.exists(save_file):
                try:
                    with open(save_file, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    player_data = save_data.get('player', {})
                    game_time_data = save_data.get('game_time', {})
                    level = player_data.get('level', '?')
                    money = player_data.get('money', '?')
                    days = game_time_data.get('days', 0)
                    months = game_time_data.get('months', 0)
                    years = game_time_data.get('years', 0)
                    hours = game_time_data.get('hours', 0)
                    minutes = game_time_data.get('minutes', 0)
                    month_str = month_name.get(months, "???")
                    slot_info = f"Слот {slot}: Ур.{level} 💰 {money} | {years}-{month_str}-{days} {hours:02d}:{minutes:02d}"
                    options.append(slot_info)
                except Exception as e:
                    options.append(f"Слот {slot}: Ошибка загрузки")
            else:
                options.append(f"Слот {slot}: Пусто")
        if cur_page > 0:
            options.append("◀ Предыдущая страница")
        if cur_page < totl_p - 1:
            options.append("Следующая страница ▶")
        options.append("Назад")
        index = 0
        while True:
            clear()
            print(f"╔{'═' * (len(title) + 4)}╗")
            print(f"║  {title}  ║")
            print(f"╚{'═' * (len(title) + 4)}╝")
            print(f"Страница {cur_page + 1}/{totl_p}")
            print()
            for i, option in enumerate(options):
                prefix = "  > " if i == index else "  "
                print(f"{prefix}{option}")
            print(f"\nУправление: W/S - выбор, A/D - страницы, Enter - выбрать, Esc - назад")
            key = get_key()
            if key == b'w':
                index = (index - 1) % len(options)
            elif key == b's':
                index = (index + 1) % len(options)
            elif key == b'a':
                if cur_page > 0:
                    cur_page -= 1
                    break
            elif key == b'd':
                if cur_page < totl_p - 1:
                    cur_page += 1
                    break
            elif key == b'\r':
                selected_option = options[index]
                if selected_option == "Назад":
                    clear()
                    return
                elif selected_option == "<- Предыдущая страница":
                    cur_page -= 1
                    break
                elif selected_option == "Следующая страница ->":
                    cur_page += 1
                    break
                else:
                    slot = int(selected_option.split(":")[0].split(" ")[1])
                    if mode == 'save':
                        save_game(str(slot))
                        return
                    else:
                        load_game(str(slot))
                        return
            elif key == b'\x1b':
                clear()
                return
def save_game(slot):
    global player
    save_data = {
        "player": player,
        "game_time": game_time.todic(),
        "current_location": current_location,
        "locations": locations,
        "quests": quests
    }
    save_path = os.path.join(SAVE_DIR, f"save_data_{slot}.json")
    try:
        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False)
        print(f"Игра сохранена в слот {slot}")
    except Exception as e:
        print(f"Ошибка сохранения: {str(e)}")
    input("Нажмите Enter, чтобы продолжить")
    clear()


def sound_settings_loading():
    global music
    save_path = os.path.join(SAVE_DIR2, "settings.json")
    try:
        with open(save_path, "r", encoding='utf-8') as f:
            sound_settings = json.load(f)
            music = sound_settings["music"]
    except FileNotFoundError:
        print("Сохранение не найдено.")
        input("Введите Enter...")
        clear()
    except Exception as e:
        input(f"Ошибка загрузки: {str(e)}")
        clear()
#Начало квеста "Песня Лунных Водопадов"
def dialog_with_ayame_in_ochaya():
    global quests, player, locations
    clear()
    slow_print("Вы приходите к месту, про которое скзала вам Аямэ.")
    slow_print("Небольшой на первый взгляд дом в японском стиле, украшенный с изысканной простотой:")
    slow_print('деревянными панелями, бумажными фонарями и миниатюрным каменным садом.')
    dial()
    slow_print('Зайдя внутрь, вы замечате множество китцуне, обслуживающих гостей.')
    slow_print('Китцуне: Добро пожаловать, господин. Аямэ-химэ ожидает вас, следуйте за мной.')
    dial()

    slow_print("Аямэ: 'Собери их все и возвращайся ко мне. Без этих артефактов врата в Бездну не откроются.'")
    slow_print("'Будь осторожен - каждый артефакт охраняют могущественные стражи.'")    
    quests["Песня Трех Источников"]["started"] = True
    quests["Песня Трех Источников"]["stages"]["dialog"]["started"] = True
    quests["Песня Трех Источников"]["stages"]["dialog"]["completed"] = True
    quests["Песня Трех Источников"]["stages"]["heart_of_water"]["started"] = True
    waterfall_actions = locations["Сад Лунных Водопадов"]["actions"]
    if "сразиться_с_духом_воды" not in waterfall_actions:
        waterfall_actions.append("сразиться_с_духом_воды")
    locations["Рыбацкая Деревня"]["connections"]["пещера"] = "Пещера Бандитов"


def main():
    global pygame
    import pygame as pygame_module

    pygame = pygame_module
    pygame.init()
    pygame.mixer.init(frequency=44100, channels=32)
    clear()
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    print()
    if not os.path.exists("first_enter.txt"):
        with open("first_enter.txt", "w", encoding="utf-8") as f:
            f.write("0")
    with open("first_enter.txt", 'r', encoding="utf-8") as f:
        cont = f.read().strip()
        if cont == "0":
            slow_print("    星野プレセント Представляет...", 0.1)
            time.sleep(3)
            clear()
            print()
            slow_print("    Используйте W/S/Enter для управления..." )
            time.sleep(3)
            clear()
            with open("first_enter.txt", 'w') as f:
                f.write('1')
            music_on_or_off()
        else:
            sound_settings_loading()
    if music["music"]:
        play_sound_with_tag("music/main_menu_them.ogg", "main_menu", lop = -1, volume = music["VOLUME_MUSIC"])
        a["main"] = True

    main_menu()


if __name__ == "__main__":
    main()
