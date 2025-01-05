import shutil

from pymongo import MongoClient
import os
import zipfile
import music_tag

client = MongoClient('localhost', 27017)
db = client['song_storage']
songs = db.songs


def get_metadata_from_song(file_path):
    """
    Extracts metadata from a song file.

    Args:
        file_path (str): Path to the song file.

    Returns:
        dict: Metadata extracted from the song file.
    """
    try:
        f = music_tag.load_file(file_path)
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
    """
    Extracts metadata from user input.

    Args:
        user_inserted_metadata (dict): Metadata provided by the user.
        file_path (str): Path to the song file.

    Returns:
        dict: Metadata extracted from the user input.
    """
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
    """
    Adds a song to Storage and inserts the metadata in the database.

    Args:
        file_path (str): Path to the song file.
        user_inserted_metadata (dict, optional): Metadata provided by the user. Defaults to None.

    Returns:
        str: Success or error message.
    """
    # adding song to Storage
    try:
        file_name = os.path.basename(file_path)
        if songs.find_one({'file_name': file_name}):
            return f"A song with the file name '{file_name}' already exists in the database."

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


def delete_song(title):
    """
    Deletes a song from Storage and its metadata from the database

    Args:
        title (str): The title of the song to delete.

    Returns:
        str: Success or error message.
    """
    try:
        matching_songs = list(songs.find({'title': title}))
        if not matching_songs:
            return "Sorry, no songs found with the given title."

        print("Found the following matches:")
        for index, song in enumerate(matching_songs, start=1):
            print(f"{index}. {song['file_name']}")

        choice = int(input("Enter the number of the song to delete: ")) - 1
        if choice < 0 or choice >= len(matching_songs):
            return "Invalid choice."

        song_to_delete = matching_songs[choice]

        confirm = input(f"Are you sure you want to delete '{song_to_delete['file_name']}'? (y/n): ").strip().lower()
        if confirm != 'y':
            return "Deletion cancelled."

        if os.path.exists(song_to_delete['file_name']):
            os.remove(song_to_delete['file_name'])

        songs.delete_one({'_id': song_to_delete['_id']})
        return f"Song '{song_to_delete['file_name']}' deleted successfully."

    except Exception as e:
        return f"Error deleting song: {e}"

def modify_metadata(title):
    """
    Modifies the metadata of a song in the database and in the corresponding file in Storage.

    Args:
        title (str): The title of the song to modify.

    Returns:
        str: Success or error message.
    """
    try:
        matching_songs = list(songs.find({'title': title}))
        if not matching_songs:
            return "Sorry, no songs found with the given title."

        print("Found the following matches:")
        for index, song in enumerate(matching_songs, start=1):
            print(f"{index}. {song['file_name']}")

        choice = int(input("Enter the number of the song to modify its metadata: ")) - 1
        if choice < 0 or choice >= len(matching_songs):
            return "Invalid choice."

        song_to_modify = matching_songs[choice]

        print("Current metadata:")
        metadata_keys = ['title', 'artist', 'album', 'year', 'genre']
        for idx, key in enumerate(metadata_keys, start=1):
            print(f"{idx}. {key.capitalize()}: {song_to_modify.get(key, 'Unknown')}")

        file_path = os.path.join('Storage', song_to_modify['file_name'])
        f = music_tag.load_file(file_path)

        while True:
            action = input("Enter the index of the metadata to modify, 'save' to save and exit, or 'cancel' to exit without saving: ").strip().lower()

            if action == 'save':
                songs.update_one({'_id': song_to_modify['_id']}, {'$set': song_to_modify}) # update database metadata

                for key in metadata_keys: # update file metadata
                    if key in song_to_modify:
                        f[key] = song_to_modify[key]
                f.save()
                return "Metadata updated successfully."
            elif action == 'cancel':
                return "Modification cancelled."

            try:
                action_index = int(action) - 1
                if action_index < 0 or action_index >= len(metadata_keys):
                    print("Invalid index. Try again.")
                    continue

                key_to_modify = metadata_keys[action_index]
                new_value = input(f"Enter new value for {key_to_modify.capitalize()}: ")
                song_to_modify[key_to_modify] = new_value

            except ValueError:
                print("Invalid input. Try again.")

    except Exception as e:
        return f"Error modifying song: {e}"


def create_save_list(output_path, criteria):
    """
    Creates a zip archive with songs matching the given criteria.

    Args:
        output_path (str): Path to save the zip archive.
        criteria (dict): Dictionary containing search criteria.

    Returns:
        str: Success or error message.
    """
    try:
        matching_songs = list(songs.find(criteria))
        if not matching_songs:
            return "No songs found matching the given criteria."

        dir_path = os.path.join('Storage', 'Archive')

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        final_path = os.path.join(dir_path, output_path)

        z = zipfile.ZipFile(final_path, "w", zipfile.ZIP_DEFLATED)
        for song in matching_songs:
            song_path = os.path.join('Storage', song['file_name'])
            if os.path.exists(song_path):
                z.write(song_path, arcname=os.path.basename(song_path))
        z.close()

        return f"Save list created successfully at {output_path}."

    except Exception as e:
        return f"Error creating save list: {e}"


def main():
    while True:
        print("1. Add song")
        print("2. Delete song")
        print("3. Modify metadata")
        print("4. Create save list")
        print("5. Exit")
        choice = input("Enter the digit of the command: ")

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
            title = input("Enter the title of the song to delete: ")
            print(delete_song(title))
        elif choice == '3':
            title = input("Enter the title of the song to modify: ")
            print(modify_metadata(title))
        elif choice == '4':
            output_path = input("Enter the output path for the save list (e.g., songs.zip): ")
            print("Enter search criteria (leave blank to skip):")
            criteria = {}
            artist = input("Artist: ")
            if artist:
                criteria['artist'] = artist
            genre = input("Genre: ")
            if genre:
                criteria['genre'] = genre
            year = input("Year: ")
            if year:
                criteria['year'] = year
            print(create_save_list(output_path, criteria))
        elif choice == '5':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
