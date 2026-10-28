"""Individual account lookup opt-in; default keeps legacy HoYoLab accounts working."""
IMPLEMENTED = frozenset({'genshin','hsr','zzz','endfield','arknights'})
ALL = ('genshin','hsr','zzz','endfield','wuthering','arknights')

def enabled(config, game):
    explicit = ((config.get('account_data') or {}).get('game_lookup') or {})
    if game in explicit:
        return explicit[game] is True
    # Arknights is only allowed at 23:59 and with explicit opt-in.
    return game in {'genshin','hsr','zzz','endfield','wuthering'}
