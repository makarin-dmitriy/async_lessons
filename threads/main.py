import sys
import requests
import shutil
import pathlib
import marshmallow
import mimetypes
import typing
import urllib3
import timing
import math
import threading
import multiprocessing
import logging


class Photo:
    """Объект фотографии."""

    def __init__(self, *, albumId: int, id: int, title: str, url: str, thumbnailUrl: str):
        """

        :param albumId: идентификатор альбома
        :param id: идентификатор фото
        :param title: название фото
        :param url: ссылка для фото
        :param thumbnailUrl: ссылка для сжатого фото
        """

        self.albumId = albumId
        self.id = id
        self.title = title
        self.url = url
        self.thumbnailUrl = thumbnailUrl

    def __repr__(self):
        return f'Photo(albumId={self.albumId} , id={self.id} , title={self.title} ,' \
               f' url={self.url} , thumbnailUrl={self.thumbnailUrl})'

    def __str__(self):
        return f'Photo(id: {self.id}, title: {self.title})'


class Album:
    """Объект альбома."""

    def __init__(self, *, userId: int, id: int, title: str, photos: list[Photo]):
        """

        :param userId: идентификатор пользователя
        :param id: идентификатор альбома
        :param title: название альбома
        :param photos: список с фото
        """

        self.userId = userId
        self.id = id
        self.title = title
        self.photos = photos

    def __repr__(self):
        return f'Album(userId={self.userId}, id={self.id}, title={self.title}, photos={self.photos})'

    def __str__(self):
        return f'Album(id: {self.id}, title: {self.title})'


class PhotoSchema(marshmallow.Schema):
    """Схема для фотографии."""

    albumId = marshmallow.fields.Integer(required=True)
    id = marshmallow.fields.Integer(required=True)
    title = marshmallow.fields.String(required=True)
    url = marshmallow.fields.Url(required=True)
    thumbnailUrl = marshmallow.fields.Url(required=True)

    @marshmallow.post_load
    def make_user(self, data: dict[str, typing.Union[int, str]], **kwargs) -> Photo:
        """

        :param data: словарь с элементами для создания экземпляра Photo
        :param kwargs:
        :return:
        """
        return Photo(**data)


class AlbumSchema(marshmallow.Schema):
    """Схема для альбома."""

    userId = marshmallow.fields.Integer()
    id = marshmallow.fields.Integer(required=True)
    title = marshmallow.fields.String(required=True)
    photos = marshmallow.fields.Nested(PhotoSchema, required=True, many=True)

    @marshmallow.post_load
    def make_user(self, data: dict[str, typing.Union[int, str]], **kwargs) -> Album:
        """

        :param data: словарь с элементами для создания экземпляра Album
        :param kwargs:
        :return:
        """
        return Album(**data)


class Client:
    """Объект для http запросов на определённый url."""

    def __new__(cls, *args, **kwargs):
        """Добавляет logger к классу.

        :param args:
        :param kwargs:
        """

        if not hasattr(cls, 'logger'):
            logger = logging.getLogger('Client')
            logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s(%(name)s): %(asctime)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            cls.logger = logger

        instance = super(Client, cls).__new__(cls)
        return instance

    def __init__(self, url: str):
        """

        :param url: url
        """

        self.url = url
        self.response = None

    def get(self, **kwargs) -> requests.models.Response:
        """
        Добавляет результат запроса к экземпляру и возвращает его.

        :param kwargs:
        :return:
        """

        try:
            response = requests.get(self.url, **kwargs)
            if response.status_code == 200:
                self.response = response
                return response
            self.logger.warning('response status not is 200')
            raise Exception('response status not is 200')
        except Exception as ex:

            self.logger.error(f'Get exception {ex.__class__.__name__}')
            raise

    def stream_get(self):
        """Вызывает метод get с stream=True аргументом."""

        self.get(stream=True)

    def get_photo_raw(self) -> urllib3.response.HTTPResponse:
        """Возвращает файлоподобнай объект.

        :return:
        """

        if not self.response:
            self.stream_get()

        return self.response.raw

    def get_data_dict(self) -> dict:
        """ Возвращает декодированные JSON данные запроса.

        :return:
        """

        if not self.response:
            self.get()

        return self.response.json()

    def get_file_extension(self) -> str:
        """Возвращает расширение файла."""

        if not self.response:
            self.get()

        return mimetypes.guess_extension(self.response.headers.get('Content-Type'))


class Storage:
    """Реализует сохранение файла."""

    def __new__(cls, *args, **kwargs):
        """Добавляет logger к классу.

        :param args:
        :param kwargs:
        """

        if not hasattr(cls, 'logger'):
            logger = logging.getLogger('Storage')
            logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s(%(name)s): %(asctime)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            cls.logger = logger

        instance = super(Storage, cls).__new__(cls)
        return instance

    def __init__(self, base_dir_name: str) -> None:
        """Добавляет базовую директорию для сохранения файлов.


        :param base_dir_name: базовая директория для сохранения.
        """

        self.base_dir = pathlib.Path(base_dir_name)

    def save_file(self, file: typing.Any, file_directory: str, file_name: str,
                  file_extension: typing.Optional[str] = None) -> None:
        """Сохраняет файл. Создаёт каталог, если он не существует.

        :param file: файлоподобный объект
        :param file_directory: каталог для сохранения
        :param file_name: название файла
        :param file_extension: расширение файла
        :return:
        """

        if file_extension:
            file_name += file_extension

        dir_path = self.base_dir / file_directory
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / file_name

        if not file_path.exists():
            with file_path.open(mode='wb') as f:
                shutil.copyfileobj(file, f)
            self.logger.debug(f'file({file_name}) saved')
        else:
            self.logger.debug(f'file({file_name}) already exists')


class JSONPlaceholderTreadCommand:
    """Класс для обработки и манипулирования данными."""

    def __new__(cls, *args, **kwargs):
        """Добавляет logger к классу.

        :param args:
        :param kwargs:
        """

        if not hasattr(cls, 'logger'):
            logger = logging.getLogger('JSONPlaceholderTreadCommand')
            logger.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(levelname)s(%(name)s): %(asctime)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)

            cls.logger = logger

        instance = super(JSONPlaceholderTreadCommand, cls).__new__(cls)
        return instance

    albums_url = 'https://jsonplaceholder.typicode.com/albums/'
    photos_url = 'https://jsonplaceholder.typicode.com/photos/'

    def __init__(self, storage: Storage, client_class: [Client], thread_count: int = 1):
        """

        :param storage:
        :param client_class:
        :param thread_count:
        """

        self.thread_count = thread_count
        self.client_class = client_class
        self.storage = storage
        self._get_albums_and_photos_valid_data()

    def _get_albums_and_photos_valid_data(self):
        """Загружает, обрабатывает и проверяет данные.

        :return:
        """

        try:
            data = {'album_data': self.client_class(self.albums_url).get_data_dict(),
                    'photo_data': self.client_class(self.photos_url).get_data_dict()
                    }
        except Exception as ex:

            self.logger.error(f'Get exception {ex.__class__.__name__}')
            sys.exit(f'Program exit with exception({ex.__class__.__name__}) in {self.__class__}')

        for album in data.get('album_data'):
            album['photos'] = list()
            for photo in data.get('photo_data'):
                if album['id'] == photo['albumId']:
                    album['photos'].append(photo)

        album_schema = AlbumSchema(many=True)
        valid_data = album_schema.load(data['album_data'])

        self.valid_data = valid_data
        self.logger.debug(f'Data downloaded and is valid')

    # @timing.timing
    def download_and_save_photos(self, album_list: list[Album]):
        """Загружает и сохраняет фотографии.

        :param album_list:
        :return:
        """

        for album in album_list:
            for photo in album.photos:

                client = self.client_class(photo.url)

                try:
                    file = client.get_photo_raw()
                except Exception:

                    self.logger.error(f'Error download file(url: {photo.url})')
                    continue

                self.storage.save_file(file, album.title,
                                       photo.title, client.get_file_extension())

    @staticmethod
    def get_list_chunk_list(lst, number):
        """Делит список на равные части.

        :param lst:
        :param number:
        :return:
        """

        n = math.ceil(len(lst) / number)

        for x in range(0, len(lst), n):
            list_chunk = lst[x: n + x]

            yield list_chunk

    @timing.timing
    def run_threads_job(self):
        """Выполняет работу в потоках.

        :return:
        """

        my_threads = list()

        for list_chunk in self.get_list_chunk_list(self.valid_data, self.thread_count):
            my_thread = threading.Thread(target=self.download_and_save_photos, args=(list_chunk,))
            my_threads.append(my_thread)
            my_thread.start()

        for thread in my_threads:
            thread.join()

        self.logger.info(f'run_threads_job method finish success!')

    @timing.timing
    def run_process_job(self):
        """Выполняет работу в процессах.

        :return:
        """

        my_processes = list()

        for list_chunk in self.get_list_chunk_list(self.valid_data, self.thread_count):
            my_process = multiprocessing.Process(target=self.download_and_save_photos, args=(list_chunk,))
            my_processes.append(my_process)
            my_process.start()

        for process in my_processes:
            process.join()

        self.logger.info(f'run_process_job method finish success!')


def main():

    storage = Storage('downloads')

    x = JSONPlaceholderTreadCommand(storage, Client, 10)
    # x.run_threads_job()
    x.run_process_job()


if __name__ == '__main__':
    main()
