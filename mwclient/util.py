# encoding=utf-8


def parse_timestamp(t):
    if t == '0000-00-00T00:00:00Z':
        return (0, 0, 0, 0, 0, 0, 0, 0)
    return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
