# **Guild Wars Reforge Quest Tracker**

Version: 1.0.0 (Production Release)  
Created by: Akito  
A modern, minimalist desktop application designed to help Guild Wars players track their progress across all campaigns (Prophecies, Factions, Nightfall, and Eye of the North) without relying on web browser tabs.  
The interface follows a Glassmorphism Dark UI/UX theme and runs entirely as a local executable.

## **Features**

* **Tri-State Quest Tracking:** Mark quests as **Not Started** (Empty), **In Progress** (Green, Italic), or **Completed** (Gold, Strikethrough).  
* **Real-Time Data Sync:** Synchronizes and updates quest lists against the official Guild Wars Wiki to ensure all side quests are included.  
* **Integrated Wiki Viewer:** Loads quest details directly into the rounded right panel, automatically hiding sidebars for a clean, focused reading experience.  
* **Global Search:** Search across all campaigns simultaneously.  
* **Time Tracking:** Records and displays the exact date/time of completion when a finished quest is selected.  
* **Safety Guaranteed:** Sync runs in the background without freezing the UI.

## **Download and Installation (Windows EXE)**

The easiest way to use the tracker is by downloading the standalone executable:

1. **Download:** Download the latest GWReforgeTracker.exe file from the [Releases page](https://github.com/Mr-Akito/GWReforgeTracker/releases).  
2. **Run:** Place the executable in any folder and run it. The application automatically creates gw1\_db.json and gw1\_user.json files to store your quest lists and progress locally.

## **Building from Source**

If you want to run the Python source code or build the executable yourself (requires Python 3.8+):

1. **Clone the Repository:**  
   git clone \[github.com/Mr-Akito/GWReforgeTracker/\](https://github.com/Mr-Akito/GWReforgeTracker/releases)  
   cd GWReforgeTracker

2. **Install Dependencies:**  
   pip install \-r requirements.txt

3. **Run the Application:**  
   python gw1\_tracker.py

4. **Create the EXE (using PyInstaller):**  
   pyinstaller \--onefile \--windowed \--icon "PATH\_TO\_YOUR\_ICON.ico" \--name "GWReforgeTracker" gw1\_tracker.py

   *(Note: The \--icon flag requires the full path to a valid .ico file.)*

## **Legal Disclaimer**

**This tool is provided completely FREE of charge and is not for sale.** It is an open-source, fan-made project.

* This application is **NOT** affiliated with, endorsed, sponsored, or approved by ArenaNet, LLC or NCSoft Corporation.
* "Guild Wars", "ArenaNet", and "NCSoft" are trademarks or registered trademarks of NCSoft Corporation.  
* All game content, quest names, images, and wiki text displayed within this application are the property of their respective owners and the Guild Wars Wiki community (licensed under GNU FDL 1.2).  
* The application's code author is **Akito**.


<img width="1402" height="932" alt="WindowView" src="https://github.com/user-attachments/assets/02c1632c-2249-42fe-b486-3c4ec17eb809" />
