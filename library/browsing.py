"""Consistent folder-first ordering and sort controls for library views."""

FOLDER_ORDER = ('position', 'pk')


def sort_options(request):
    column = request.GET.get('sort', 'date')
    if column not in {'name', 'date'}:
        column = 'date'
    direction = request.GET.get('direction', 'desc' if column == 'date' else 'asc')
    if direction not in {'asc', 'desc'}:
        direction = 'desc' if column == 'date' else 'asc'
    def link(target):
        params = request.GET.copy()
        params.pop('page', None)
        params['sort'] = target
        params['direction'] = ('desc' if direction == 'asc' else 'asc') if target == column else ('asc' if target == 'name' else 'desc')
        return '?' + params.urlencode()
    field = 'name' if column == 'name' else 'created_at'
    prefix = '-' if direction == 'desc' else ''
    return (prefix + field, prefix + 'pk'), {
        'sort_column': column, 'sort_direction': direction,
        'sort_name_url': link('name'), 'sort_date_url': link('date'),
    }
