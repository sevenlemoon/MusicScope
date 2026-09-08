"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Language = "zh" | "en";
export const DEFAULT_LANGUAGE: Language = "zh";
type Dictionary = Record<string, string>;

const zh: Dictionary = {
  "nav.home": "首页", "nav.forYou": "为你推荐", "nav.myMusic": "我的音乐", "nav.concerts": "演出查询", "nav.lab": "音轨分离", "nav.timeline": "时间线", "nav.primary": "主导航",
  "status.loading": "正在加载…", "status.error": "操作失败，请重试。", "status.imported": "已导入 {count} 条记录。", "status.completed": "已完成", "status.pending": "等待中", "status.processing": "处理中", "status.failed": "失败",
  "home.title": "让音乐看见更大的你", "home.open": "进入", "home.heroKicker": "从你的音乐开始", "home.importTitle": "导入你的音乐", "home.importDescription": "歌单导入只建立真实音乐库，不虚构收听行为。",
  "v3.heroTitle": "让音乐，看见更大的你", "v3.heroBody": "从你的收藏出发，发现新的音乐、遇见现场、探索声音的更多可能。", "v3.start": "开始探索", "v3.libraryStats": "音乐库统计", "v3.coreTitle": "四种方式，打开你的音乐世界",
  "v3.featureDiscover": "用真实收藏与可解释证据找到下一首。", "v3.featureLive": "搜索喜欢的艺术家是否有近期现场。", "v3.featureLibrary": "浏览歌曲、艺术家与已有音乐元数据。", "v3.featureStems": "用真实 AI 模型分离人声与伴奏。",
  "v3.importTitle": "把你的音乐带进来", "v3.importIntro": "可靠导入，保留来源；歌单不等于播放历史。", "v3.libraryIntro": "这是你的收藏，不是虚构的收听档案。", "v3.librarySearch": "搜索歌曲、艺人或流派",
  "v3.tab.tracks": "歌曲", "v3.tab.artists": "艺人", "v3.tab.genres": "流派", "v3.importMusic": "导入音乐", "v3.metadataPending": "元数据待补充", "v3.findConcert": "查询演出", "v3.trackCount": "{count} 首歌曲在你的音乐库中",
  "v3.noGenres": "流派信息待补充", "v3.noGenresBody": "当前歌单只包含歌曲与艺术家。MusicScope 不会猜测流派。", "v3.noGenreMatches": "没有匹配的流派", "v3.discoverTitle": "从熟悉出发，向未知延伸。", "v3.discoverIntro": "每一条推荐都有可追溯的理由。", "v3.explorationHonest": "探索度改变匹配与新鲜感的平衡，不会随机塞入歌曲。",
  "v3.role.precise": "精准推荐", "v3.role.similar": "相似发现", "v3.role.explore": "探索推荐", "v3.concertTitle": "想看谁的演出？", "v3.concertIntro": "先从你的音乐库选择艺术家，也可以直接输入名字。", "v3.concertPlaceholder": "搜索音乐库中的艺人…", "v3.concertNone": "暂未查询到该艺人的近期公开演出。",
  "v3.importResolving": "正在识别 {count} 首歌曲", "v3.importRefresh": "正在刷新音乐库…", "v3.importCompleteRefreshFailed": "已导入 {count} 条记录，但音乐库统计刷新失败，请稍后重新打开页面。",
};
const en: Dictionary = {
  "nav.home": "Home", "nav.forYou": "For You", "nav.myMusic": "My Music", "nav.concerts": "Concert Search", "nav.lab": "Stem Separation", "nav.timeline": "Timeline", "nav.primary": "Primary navigation",
  "status.loading": "Loading…", "status.error": "Something went wrong. Try again.", "status.imported": "Imported {count} records.", "status.completed": "Complete", "status.pending": "Pending", "status.processing": "Processing", "status.failed": "Failed",
  "home.title": "Your music, a wider world", "home.open": "Enter", "home.heroKicker": "Start with your music", "home.importTitle": "Import your music", "home.importDescription": "Playlist import creates an honest library, not fabricated behavior.",
  "v3.heroTitle": "Let your music open a wider world", "v3.heroBody": "Start with your collection. Discover music, find live shows, and explore sound in new ways.", "v3.start": "Start exploring", "v3.libraryStats": "Library statistics", "v3.coreTitle": "Four ways into your music",
  "v3.featureDiscover": "Find what comes next through real library evidence.", "v3.featureLive": "Search upcoming shows for artists you care about.", "v3.featureLibrary": "Browse tracks, artists, and available metadata.", "v3.featureStems": "Separate vocals and instrumental with a real AI model.",
  "v3.importTitle": "Bring your music in", "v3.importIntro": "Reliable import with provenance; a playlist is not listening history.", "v3.libraryIntro": "Your collection, without invented listening behavior.", "v3.librarySearch": "Search tracks, artists, or genres",
  "v3.tab.tracks": "Tracks", "v3.tab.artists": "Artists", "v3.tab.genres": "Genres", "v3.importMusic": "Import music", "v3.metadataPending": "Metadata pending", "v3.findConcert": "Find concerts", "v3.trackCount": "{count} tracks in your library",
  "v3.noGenres": "Genre metadata pending", "v3.noGenresBody": "Your playlist contains titles and artists. MusicScope will not guess genres.", "v3.noGenreMatches": "No genres match your search", "v3.discoverTitle": "From familiar ground into the unknown.", "v3.discoverIntro": "Every recommendation comes with traceable evidence.", "v3.explorationHonest": "Exploration changes fit and novelty; it does not inject random tracks.",
  "v3.role.precise": "Precise recommendation", "v3.role.similar": "Similar discovery", "v3.role.explore": "Exploration pick", "v3.concertTitle": "Who do you want to see?", "v3.concertIntro": "Choose an artist from your library or type any artist name.", "v3.concertPlaceholder": "Search artists in your library…", "v3.concertNone": "No upcoming public shows were found for this artist.",
  "v3.importResolving": "Identifying {count} tracks", "v3.importRefresh": "Refreshing your library…", "v3.importCompleteRefreshFailed": "Imported {count} records, but library statistics could not refresh. Reopen the page shortly.",
};

Object.assign(zh, {
  "playlist.step1": "准备", "playlist.step2": "获取歌曲列表", "playlist.step3": "导入音乐库", "playlist.otherMethods": "CSV 导入", "playlist.membershipNote": "歌单导入代表收藏关系，不会被记录为播放次数或近期收听。",
  "playlist.placeholder": "粘贴 NetEase Cloud Music 歌单链接", "playlist.detect": "检测链接", "playlist.invalid": "请提供有效内容。", "playlist.checking": "正在检查歌单…", "playlist.unsupported": "无法从链接可靠读取完整曲目，请使用辅助工具复制歌曲文本。", "playlist.csvReady": "准备好后开始导入。", "playlist.textTab": "歌单文本", "playlist.textHelp": "复制歌单链接到辅助工具，再把 Track - Artist 文本粘贴到这里。", "playlist.openTool": "打开歌单转换工具 ↗", "playlist.textPlaceholder": "Track Name - Artist", "playlist.parse": "建立音乐库", "playlist.summary": "共 {total} 行 · 有效 {valid} · 待处理 {invalid} · 艺术家 {artists}", "playlist.stageParse": "正在解析文本…", "playlist.complete": "导入完成 · {count} 首歌曲 · {artists} 位艺术家 · {unresolved} 条待处理", "playlist.attribution": "转换工具由第三方开源项目提供；MusicScope 不需要你的密码。", "playlist.csv": "选择 CSV 文件",
  "profile.none": "暂无", "profile.searchLibrary": "搜索你的音乐库", "profile.libraryEmpty": "你的音乐库还是空的。", "profile.dataManagement": "数据与修正", "profile.dataManagementHint": "导入来源、待处理记录与纠错工具", "profile.showingFirst": "当前显示前 {count} 首", "profile.showingFirstOf": "当前显示前 {count} 首匹配歌曲，共 {total} 首", "profile.showingFirstArtists": "当前显示前 {count} 位匹配艺人，共 {total} 位",
  "import.batches": "导入记录", "import.summary": "共 {total} 次导入 · {withRecords} 次有记录 · {empty} 次为空", "import.showAll": "显示全部", "import.showLess": "收起", "import.records": "{count} 条记录", "import.empty": "空导入", "import.resolved": "已匹配", "import.ambiguous": "有歧义", "import.unresolved": "未匹配",
  "review.title": "待处理", "review.none": "没有待处理的记录。", "review.assign": "分配曲目…", "review.exclude": "排除",
  "recommendation.familiar": "熟悉", "recommendation.adventurous": "探索", "recommendation.exploration": "探索度", "recommendation.why": "为什么推荐？", "recommendation.noCandidates": "音乐库内容还不足以生成推荐。", "recommendation.unavailable": "推荐暂时不可用，请确认 API 已启动。",
  "feedback.like": "喜欢", "feedback.skip": "暂时不想听", "feedback.dislike": "不喜欢", "feedback.dislikeArtist": "不喜欢这个艺人", "feedback.dislikeStyle": "不喜欢这种风格", "feedback.simplyDislike": "就是不喜欢", "feedback.submitting": "正在记录…", "feedback.recorded": "已记录", "feedback.error": "记录失败，请重试。", "feedback.retry": "重试",
  "evidence.long_term_genre": "匹配你收藏中的 {value}", "evidence.artist_affinity": "来自你音乐库中熟悉的艺术家", "evidence.short_term_state": "与已有音乐偏好相近", "evidence.relationship": "建立在你的收藏关系上", "evidence.novelty": "带来较少出现的艺术家", "evidence.exploration": "在较高探索度下拓宽边界", "evidence.feedback_penalty": "已根据你的反馈调整", "evidence.balanced_match": "平衡了收藏匹配、新鲜感与多样性",
  "lab.description": "上传本地音频，使用 Demucs 生成同步的人声与伴奏音轨，并实时独立调节音量。",
  "audio.eyebrow": "AI 音频分离", "audio.title": "上传声音，拆分层次", "audio.description": "真实离线分离；不伪造处理进度。", "audio.choose": "选择或拖入音频", "audio.formats": "WAV、MP3、M4A/AAC 或 FLAC · 最长 15 分钟", "audio.separate": "开始分离", "audio.retry": "重试", "audio.vocals": "人声", "audio.instrumental": "伴奏", "audio.play": "播放", "audio.pause": "暂停", "audio.seek": "定位", "audio.loaded": "两条音轨已加载", "audio.ready": "分离完成，可以播放", "audio.chooseMessage": "选择音频以创建同步音轨。", "audio.uploading": "ANALYZING · 正在验证音频", "audio.complete": "RENDERING COMPLETE · 两条音轨已生成", "audio.normalized": "SEPARATING · 音频已标准化", "audio.cached": "缓存结果已准备好。", "audio.processing": "SEPARATING · 正在分离人声和伴奏", "audio.queued": "等待分离…", "audio.failed": "分离失败，请重试。", "audio.unavailable": "音频服务不可用，请确认 API 和 FFmpeg 已启动。", "audio.loading": "正在加载两条音轨…", "audio.playing": "正在播放同步音轨。", "audio.loadError": "两条音轨加载失败，请重试。",
  "concert.search": "艺术家搜索", "concert.searchButton": "查询演出", "concert.searching": "查询中…", "concert.error": "演出服务暂不可用，请稍后重试。", "concert.providerUnavailable": "暂时无法获取该艺人的实时演出信息。", "concert.title": "即将举行的演出", "concert.venueUnavailable": "场地信息暂未公布", "concert.details": "查看详情 ↗",
});

Object.assign(en, {
  "playlist.step1": "Prepare", "playlist.step2": "Get track list", "playlist.step3": "Build library", "playlist.otherMethods": "CSV import", "playlist.membershipNote": "Playlist import means library membership, not plays or recent listening.", "playlist.placeholder": "Paste a NetEase Cloud Music playlist link", "playlist.detect": "Check link", "playlist.invalid": "Provide valid content.", "playlist.checking": "Checking playlist…", "playlist.unsupported": "The full list cannot be read reliably. Copy track text with the helper.", "playlist.csvReady": "Ready when you are.", "playlist.textTab": "Playlist text", "playlist.textHelp": "Use the helper, then paste Track - Artist text here.", "playlist.openTool": "Open playlist helper ↗", "playlist.textPlaceholder": "Track Name - Artist", "playlist.parse": "Build library", "playlist.summary": "{total} lines · {valid} valid · {invalid} for review · {artists} artists", "playlist.stageParse": "Parsing text…", "playlist.complete": "Import complete · {count} tracks · {artists} artists · {unresolved} for review", "playlist.attribution": "The converter is a third-party open-source helper; MusicScope never needs your password.", "playlist.csv": "Choose CSV file",
  "profile.none": "Unknown", "profile.searchLibrary": "Search your library", "profile.libraryEmpty": "Your music library is empty.", "profile.dataManagement": "Data and corrections", "profile.dataManagementHint": "Import provenance, review, and correction tools", "profile.showingFirst": "Showing the first {count}", "profile.showingFirstOf": "Showing the first {count} of {total} matching tracks", "profile.showingFirstArtists": "Showing the first {count} of {total} matching artists",
  "import.batches": "Import history", "import.summary": "{total} imports · {withRecords} with records · {empty} empty", "import.showAll": "Show all", "import.showLess": "Show less", "import.records": "{count} records", "import.empty": "Empty import", "import.resolved": "resolved", "import.ambiguous": "ambiguous", "import.unresolved": "unresolved",
  "review.title": "Needs review", "review.none": "No records need review.", "review.assign": "Assign track…", "review.exclude": "Exclude",
  "recommendation.familiar": "Familiar", "recommendation.adventurous": "Explore", "recommendation.exploration": "Exploration", "recommendation.why": "Why this?", "recommendation.noCandidates": "There is not enough library data for recommendations yet.", "recommendation.unavailable": "Recommendations are unavailable until the API is ready.",
  "feedback.like": "Like", "feedback.skip": "Not now", "feedback.dislike": "Dislike", "feedback.dislikeArtist": "Dislike this artist", "feedback.dislikeStyle": "Dislike this style", "feedback.simplyDislike": "Simply dislike", "feedback.submitting": "Recording…", "feedback.recorded": "Recorded", "feedback.error": "Could not record feedback.", "feedback.retry": "Retry",
  "evidence.long_term_genre": "matches a {value} in your library", "evidence.artist_affinity": "comes from a familiar artist in your library", "evidence.short_term_state": "is close to your established music preferences", "evidence.relationship": "builds on your library relationship", "evidence.novelty": "brings in a less familiar artist", "evidence.exploration": "widens the boundary at this exploration level", "evidence.feedback_penalty": "has been adjusted using your feedback", "evidence.balanced_match": "balances library fit, freshness, and diversity",
  "lab.description": "Upload local audio, separate synchronized vocals and instrumental with Demucs, and control both gains live.",
  "audio.eyebrow": "AI separation", "audio.title": "Upload sound, reveal layers", "audio.description": "Real offline separation with honest processing states.", "audio.choose": "Choose or drop audio", "audio.formats": "WAV, MP3, M4A/AAC, or FLAC · max 15 minutes", "audio.separate": "Separate", "audio.retry": "Retry", "audio.vocals": "Vocals", "audio.instrumental": "Instrumental", "audio.play": "Play", "audio.pause": "Pause", "audio.seek": "Seek", "audio.loaded": "Both stems loaded", "audio.ready": "Separation ready", "audio.chooseMessage": "Choose audio to create synchronized stems.", "audio.uploading": "ANALYZING · validating audio", "audio.complete": "RENDERING COMPLETE · both stems are ready", "audio.normalized": "SEPARATING · audio normalized", "audio.cached": "Cached separation is ready.", "audio.processing": "SEPARATING · vocals and instrumental", "audio.queued": "Queued for separation…", "audio.failed": "Separation failed. Try again.", "audio.unavailable": "Audio service unavailable. Check the API and FFmpeg.", "audio.loading": "Loading both stems…", "audio.playing": "Playing synchronized stems.", "audio.loadError": "Both stems must load before playback.",
  "concert.search": "Artist search", "concert.searchButton": "Find shows", "concert.searching": "Searching…", "concert.error": "Concert service unavailable. Try again later.", "concert.providerUnavailable": "Live concert information is temporarily unavailable.", "concert.title": "Upcoming concert", "concert.venueUnavailable": "Venue not announced", "concert.details": "View details ↗",
});

export function translate(language: Language, key: string, values?: Record<string, string | number>): string {
  let result = (language === "zh" ? zh : en)[key] ?? en[key] ?? key;
  Object.entries(values ?? {}).forEach(([name, value]) => { result = result.replace(`{${name}}`, String(value)); });
  return result;
}

type I18nValue = { language: Language; setLanguage: (language: Language) => void; t: (key: string, values?: Record<string, string | number>) => string };
const I18nContext = createContext<I18nValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>(DEFAULT_LANGUAGE);
  useEffect(() => { const saved = window.localStorage.getItem("musicscope-language"); if (saved === "zh" || saved === "en") setLanguage(saved); }, []);
  useEffect(() => { document.documentElement.lang = language === "zh" ? "zh-CN" : "en"; }, [language]);
  const changeLanguage = (next: Language) => { setLanguage(next); window.localStorage.setItem("musicscope-language", next); };
  const value = useMemo(() => ({ language, setLanguage: changeLanguage, t: (key: string, values?: Record<string, string | number>) => translate(language, key, values) }), [language]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside LanguageProvider");
  return value;
}
