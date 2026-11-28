import random

SESSION_WELCOME_KEY = 'landing_welcome_pending'

WELCOME_MESSAGES = (
    '今天也要加油呀！',
    '你已经很棒了，继续保持！',
    '每一份努力，都会发光。',
    '学习路上，你很耀眼。',
    '相信自己，你比想象中更厉害。',
    '又见面啦，愿你今天收获满满。',
    '慢慢来，也是在进步。',
    '你的坚持，终会开花结果。',
    '今日份的你，值得一句赞叹。',
    '认真学习的你，真好看。',
    '愿你所求皆如愿，所行皆坦途。',
    '小步前进，也是向前的胜利。',
    '知识会奖励每一个用心的人。',
    '今天又是充满希望的一天！',
    '保持好奇，世界会给你惊喜。',
    '再坚持一下，你就又近了一步。',
    '你的认真，大家都看得见。',
    '累了就歇一歇，但别放弃呀。',
    '这次登录，也是一次小小的胜利。',
    '班级因有你而更有活力。',
    '把今天过好，就是了不起的事。',
    '你正在变成更好的自己。',
    '愿今天的作业都对你温柔一点。',
    '抬头看看，阳光也在为你加油。',
)


def pick_welcome_message(nickname=''):
    message = random.choice(WELCOME_MESSAGES)
    if nickname:
        return f'{nickname}，{message}'
    return message