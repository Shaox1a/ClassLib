from django.shortcuts import render


FOLDER_CATEGORIES = (
    {'id': 1, 'name': '语文', 'description': '课件、讲义与阅读资料'},
    {'id': 2, 'name': '英语', 'description': '课件、单词与阅读资料'},
    {'id': 3, 'name': '数学', 'description': '课件、练习题与复习资料'},
    {'id': 4, 'name': '物理', 'description': '课件、实验与复习资料'},
    {'id': 5, 'name': '化学', 'description': '课件、实验与复习资料'},
    {'id': 6, 'name': '公共资料', 'description': '班级共享资料'},
)


def home(request):
    return render(request, 'library/home.html', {'folders': FOLDER_CATEGORIES})


def folder_detail(request, folder_id):
    folder = next((item for item in FOLDER_CATEGORIES if item['id'] == folder_id), None)
    if folder is None:
        from django.http import Http404

        raise Http404('Folder does not exist')
    return render(request, 'library/folder.html', {'folder': folder, 'files': []})


def file_detail(request, file_id):
    return render(request, 'library/file.html', {'file_id': file_id})


def search(request):
    query = request.GET.get('q', '').strip()
    return render(
        request,
        'library/search.html',
        {'query': query, 'results': [], 'has_searched': bool(query)},
    )
