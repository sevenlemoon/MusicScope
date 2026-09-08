# NetEase Cloud Music playlist import

The graduation-demo URL `https://music.163.com/m/playlist?id=5036528042&creatorId=3346225720` was tested from the local development environment.

The public page reliably exposed the playlist ID, title (`7ningning喜欢的音乐`), creator (`7ningning`), declared track count (2506), cover art URL, and six preview track IDs/names. The complete list was delivered as an encrypted client-side payload. No supported, stable local endpoint was found that returned the complete track metadata without relying on undocumented reverse-engineered behavior.

MusicScope therefore does not claim to import this playlist URL directly. The UI detects NetEase links and reports the provider limitation. If a user obtains plain track lines through an allowed local workflow, the assisted playlist-text import creates library membership and canonical provisional tracks without inventing plays; CSV/manual listening-history import remains the reliable behavioral baseline.
