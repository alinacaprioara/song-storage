import shutil

from pymongo import MongoClient
import pymongo.errors as pymongo_err
import os
import zipfile
import music_tag
import pygame

client = MongoClient('localhost', 27017)
db = client['song_storage']
songs = db.songs


def get_metadata_from_song(file_path=None):
    """
    Extract metadata from a song file.

    Args:
        file_path (str): Path to the song file.

    Returns:
        dict: Metadata extracted from the song file or default values if an exception occurs.

    Raises:
        ValueError: If no file path is provided.
        FileNotFoundError: If the file is not found.
    """

    try:
        if not file_path:
            raise ValueError("No file path provided.")
        if not os.path.exists(file_path):
            raise FileNotFoundError("File not found.")

        f = music_tag.load_file(file_path)
        metadata = {
            'file_name': os.path.basename(file_path),
            'title': str(f['title']) if str(f['title']).strip() else 'Unknown',
            'artist': str(f['artist']) if str(f['artist']).strip() else 'Unknown Artist',
            'album': str(f['album']) if str(f['album']).strip() else 'Unknown Album',
            'year': str(f['year']) if str(f['year']).strip() else 'Unknown Year',
            'genre': str(f['genre']) if str(f['genre']).strip() else 'Unknown Genre'
        }
        return metadata

    except Exception as e:
        print(f"Error extracting metadata, setting default values: {e}")
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
    Extract metadata from user input.

    Args:
        user_inserted_metadata (dict): Metadata provided by the user.
        file_path (str): Path to the song file.

    Returns:
        dict: Metadata extracted from the user input.

    Raises:
        ValueError: If no file path is provided.
        FileNotFoundError: If the file is not found.
    """
    if not file_path:
        raise ValueError("No file path provided.")
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found.")

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
    Add a song to Storage and insert the metadata in the database.

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

        # adding song to Storage
        song_path = os.path.join('Storage', os.path.basename(file_path))
        try:
            shutil.copy(file_path, song_path)
        except PermissionError as e:
            return f"Permission error: {e}"
        except shutil.Error as e:
            return f"Error copying file: {e}"

        # adding metadata to database
        if user_inserted_metadata:
            metadata = get_metadata_from_user(user_inserted_metadata, file_path)
        else:
            metadata = get_metadata_from_song(file_path)

        try:
            res = songs.insert_one(metadata)
        except pymongo_err.PyMongoError as e:
            return f"Error inserting metadata: {e}"

        return f"Song added with id: {res.inserted_id}"

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: {e}"


def delete_song(title):
    """
    Delete a song from Storage and its metadata from the database

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

        # deleting song from Storage
        try:
            if os.path.exists(song_to_delete['file_name']):
                os.remove(song_to_delete['file_name'])
        except PermissionError as e:
            return f"Permission error: {e}"

        # deleting metadata from database
        try:
            songs.delete_one({'_id': song_to_delete['_id']})
        except pymongo_err.PyMongoError as e:
            return f"Error deleting metadata: {e}"

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
    Create a zip archive with songs matching the given criteria.

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
            try:
                os.makedirs(dir_path)
            except PermissionError as e:
                return f"Permission error: {e}"
            except OSError as e:
                return f"Error creating directory: {e}"

        final_path = os.path.join(dir_path, output_path)

        try:
            with zipfile.ZipFile(final_path, "w", zipfile.ZIP_DEFLATED) as z:
                for song in matching_songs:
                    song_path = os.path.join('Storage', song['file_name'])
                    if os.path.exists(song_path):
                        z.write(song_path, arcname=os.path.basename(song_path))
                    else:
                        print(f"Warning: File '{song_path}' not found. Skipping.")
        except PermissionError as e:
            return f"Permission error: {e}"
        except zipfile.BadZipfile as e:
            return f"Error creating zip archive: {e}"

        return f"Save list created successfully at {output_path}."

    except Exception as e:
        return f"Error creating save list: {e}"


def search(criteria):
    """
    Search for songs in the database based on given criteria and return their metadata.

    Args:
        criteria (dict): Dictionary containing search criteria.

    Returns:
        str: Metadata of matching songs or a message if no matches are found.
    """
    try:
        format_criteria = criteria.pop('format', None)

        matching_songs = list(songs.find(criteria))
        if not matching_songs:
            return "No songs found matching the given criteria."

        if format_criteria:
            matching_songs = [song for song in matching_songs
                              if song.get('file_name', '').split('.')[-1] == format_criteria]
            if not matching_songs:
                return f"No songs found matching the format '{format_criteria}'."

        result = "Matching songs:\n"
        for index, song in enumerate(matching_songs, start=1):
            result += f"{index}. Title: {song.get('title', 'Unknown')}, Artist: {song.get('artist', 'Unknown')}, " \
                      f"Album: {song.get('album', 'Unknown')}, Year: {song.get('year', 'Unknown')}, " \
                      f"Genre: {song.get('genre', 'Unknown')}, File Name: {song.get('file_name', 'Unknown')}\n"
        return result
    except Exception as e:
        return f"Error searching songs: {e}"


def play_song(title):
    """
    Plays a song.

    Args:
        title (str): The title of the song to play.

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

        choice = int(input("Enter the number of the song to play: ")) - 1
        if choice < 0 or choice >= len(matching_songs):
            return "Invalid choice."

        song_to_play = matching_songs[choice]

        file_path = os.path.join('Storage', song_to_play['file_name'])
        pygame.init()
        chosen_song = pygame.mixer.Sound(file_path)
        chosen_song.play()
        print(f"Now playing '{song_to_play['file_name']}'.")
        # press pause or stop
        while True:
            action = input("Enter 'pause' to pause the song, 'stop' to stop the song, 'start' to start it, 'exit' to exit: ").strip().lower()
            if action == 'pause':
                pygame.mixer.pause()
            elif action == 'stop':
                pygame.mixer.stop()
            elif action == 'start':
                if pygame.mixer.get_busy():
                    pygame.mixer.unpause()
                else:
                    chosen_song.play()
            elif action == 'exit':
                pygame.quit()
                return "Song stopped."
            else:
                print("Invalid action. Try again.")
    except Exception as e:
        return f"Error playing song: {e}"

def main():
    while True:
        print("1. Add song")
        print("2. Delete song")
        print("3. Modify metadata of a song")
        print("4. Create archive of songs")
        print("5. Search song")
        print("6. Play song")
        print("7. Exit")
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
            print("Enter search criteria (leave blank to skip):")
            criteria = {}
            title = input("Title: ")
            if title:
                criteria['title'] = title
            artist = input("Artist: ")
            if artist:
                criteria['artist'] = artist
            album = input("Album: ")
            if album:
                criteria['album'] = album
            year = input("Year: ")
            if year:
                criteria['year'] = year
            genre = input("Genre: ")
            if genre:
                criteria['genre'] = genre
            format_criteria = input("Format (e.g., mp3): ")
            if format_criteria:
                criteria['format'] = format_criteria
            print(search(criteria))
        elif choice == '6':
            title = input("Enter the title of the song to play: ")
            print(play_song(title))
        elif choice == '7':
            break
        else:
            print("Invalid choice")

        input("\033[35mPress Enter to return to main menu...\033[0m")

if __name__ == "__main__":
    main()
