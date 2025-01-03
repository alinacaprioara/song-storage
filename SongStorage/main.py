import shutil

from pymongo import MongoClient
import os
import zipfile
import music_tag


client = MongoClient('localhost', 27017)
db = client['song_storage']
songs = db.songs

# TODO: metadata handling is different for ogg files, research also on wav files

def get_metadata_from_song(file_path):

    try:
        f = music_tag.load_file(file_path)
        print(f)
        metadata = {
            'file_name': os.path.basename(file_path),
            'title': str(f['title']),
            'artist': str(f['artist']),
            'album': str(f['album']),
            'year': str(f['year']),
            'genre': str(f['genre'])
            # de vazut la genre ca nu prea exista in metadate
        }
        return metadata
    except Exception as e:
        print(e)
        return {
            'file_name': os.path.basename(file_path),
            'title': 'Unknown',
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'year': 'Unknown Year',
            'genre': 'Unknown Genre'
        }


def get_metadata_from_user(user_inserted_metadata, file_path):

    metadata = {
        'file_name': os.path.basename(file_path),
        'title': user_inserted_metadata.get('title', 'Unknown'),
        'artist': user_inserted_metadata.get('artist', 'Unknown Artist'),
        'album': user_inserted_metadata.get('album', 'Unknown Album'),
        'year': user_inserted_metadata.get('year', 'Unknown Year'),
        'genre': user_inserted_metadata.get('genre', 'Unknown Genre')
    }
    return metadata



def add_song(file_path, user_inserted_metadata=None):
    # adding song to Storage
    try:
        if not os.path.exists('Storage'):
            os.makedirs('Storage')

        song_path = os.path.join('Storage', os.path.basename(file_path))
        shutil.copy(file_path, song_path)

    # adding metadata to database

        if user_inserted_metadata:
            metadata = get_metadata_from_user(user_inserted_metadata, file_path)
        else:
            metadata = get_metadata_from_song(file_path)

        res = songs.insert_one(metadata)
        return f"Song added with id: {res.inserted_id}"

    except Exception as e:
        return f"Error: {e}"


def main():

    while True:
        print("1. Add song")
        print("2. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            file_path = input("Please provide file_path of the song: ")
            if file_path.endswith('"'):
                file_path = file_path[1:-1]
            user_metadata = input("Enter metadata for the song? (y/n): ").strip().lower()
            if user_metadata == 'y':
                print("Press enter to skip a field")
                title = input("Enter title: ") or None
                artist = input("Enter artist: ") or None
                album = input("Enter album: ") or None
                year = input("Enter year: ") or None
                genre = input("Enter genre: ") or None
                user_inserted_metadata = {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'year': year,
                    'genre': genre
                }
            else:
                user_inserted_metadata = None
            print(add_song(file_path, user_inserted_metadata))
        elif choice == '2':
            break
        else:
            print("Invalid choice")



if __name__ == "__main__":
    main()