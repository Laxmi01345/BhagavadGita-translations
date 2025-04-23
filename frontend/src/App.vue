<script setup>
import 'primeicons/primeicons.css'
import { ref, onMounted, computed, watch } from "vue";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const chapters = ref([]);
const verses = ref({});
const activeChapter = ref(null);
const activeVerseIndex = ref(null);
const videoPlayers = ref({});
const currentVideoTime = ref(0);
const isLoading = ref(true);
const darkMode = ref(false);

// Time markers for verses in each chapter
const verseTimeMarkers = ref({});

// Track which verse is currently being played/highlighted
const highlightedVerseIndex = ref(null);

// Flag to track if playback has been initiated at least once
const playbackInitiated = ref(false);

onMounted(async () => {
  try {
    console.log('Using API URL:', API_URL); // Debug log
    const response = await axios.get(`${API_URL.replace(/\/$/, "")}/chapters`);

    console.log('Chapters response:', response.data); // Debug log
    
    if (!response.data || !Array.isArray(response.data)) {
      throw new Error('Invalid chapters data received');
    }

    // Remove duplicate mapping and fix video_url handling
    chapters.value = response.data.map(chapter => {
      const videoIdMatch = chapter.video_url?.match(/(?:v=|\/)([0-9A-Za-z_-]{11})/);
      const videoId = videoIdMatch ? videoIdMatch[1] : null;
      console.log('Processing chapter:', chapter.chapter_id, 'videoId:', videoId); // Debug log

      return {
        ...chapter,
        videoId,
        embedUrl: videoId ? `https://www.youtube.com/embed/${videoId}?enablejsapi=1` : null
      };
    });

    // Set first chapter as active by default
    if (chapters.value.length > 0) {
      await loadChapter(chapters.value[0].chapter_id);
    }
    
    isLoading.value = false;
  } catch (error) {
    console.error('Error fetching chapters:', error);
    isLoading.value = false;
  }
  
  loadYouTubeAPI();
});

const loadYouTubeAPI = () => {
  // Load the YouTube iframe API if not already loaded
  if (!window.YT) {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
  }
};

const initializePlayer = (chapterId) => {
  if (!chapters.value.find(c => c.chapter_id === chapterId)?.videoId) return;
  
  const videoId = chapters.value.find(c => c.chapter_id === chapterId).videoId;
  
  // Initialize YouTube player when API is ready
  if (window.YT && window.YT.Player) {
    videoPlayers.value[chapterId] = new window.YT.Player(`youtube-player-${chapterId}`, {
      videoId: videoId,
      events: {
        'onReady': () => {
          console.log(`Player for chapter ${chapterId} ready`);
          // Once player is ready, generate sample time markers
          generateSampleTimeMarkers(chapterId);
        },
        'onStateChange': (event) => handlePlayerStateChange(event, chapterId)
      },
      playerVars: {
        playsinline: 1,
        modestbranding: 1,
        rel: 0
      }
    });
  } else {
    // Wait for API to load
    window.onYouTubeIframeAPIReady = () => {
      initializePlayer(chapterId);
    };
  }
};

// Generate sample time markers based on video duration and number of verses
const generateSampleTimeMarkers = (chapterId) => {
  const player = videoPlayers.value[chapterId];
  if (!player || typeof player.getDuration !== 'function') return;
  
  const chapterVerses = verses.value[chapterId] || [];
  if (chapterVerses.length === 0) return;
  
  const videoDuration = player.getDuration();
  const verseCount = chapterVerses.length;
  
  // Distribute verses evenly across video duration (with some buffer)
  const introTime = 20; // 20 seconds intro
  const verseDuration = (videoDuration - introTime) / verseCount;
  
  const markers = [];
  
  for (let i = 0; i < verseCount; i++) {
    markers.push({
      start: introTime + (i * verseDuration),
      end: introTime + ((i + 1) * verseDuration),
      verseIndex: i
    });
  }
  
  verseTimeMarkers.value[chapterId] = markers;
};

const handlePlayerStateChange = (event, chapterId) => {
  if (event.data === window.YT.PlayerState.PLAYING) {
    // Mark that playback has been initiated at least once
    playbackInitiated.value = true;
    
    // Start time tracking
    startTimeTracking(chapterId);
  } else if (event.data === window.YT.PlayerState.PAUSED || event.data === window.YT.PlayerState.ENDED) {
    // Stop time tracking only if the video is paused manually
    // We don't want to stop if it's just transitioning between verses
    if (event.data === window.YT.PlayerState.PAUSED) {
      stopTimeTracking();
    }
    
    // If video ended, reset the highlighted verse
    if (event.data === window.YT.PlayerState.ENDED) {
      highlightedVerseIndex.value = null;
      activeVerseIndex.value = null;
      playbackInitiated.value = false;
    }
  }
};

let timeTrackingInterval = null;

const startTimeTracking = (chapterId) => {
  // Clear any existing interval
  stopTimeTracking();
  
  // Set up new interval
  timeTrackingInterval = setInterval(() => {
    if (videoPlayers.value[chapterId] && typeof videoPlayers.value[chapterId].getCurrentTime === 'function') {
      currentVideoTime.value = videoPlayers.value[chapterId].getCurrentTime();
      
      // Find active verse based on current time
      updateActiveVerseByTime(chapterId);
    }
  }, 500); // Check twice per second for smoother updates
};

const stopTimeTracking = () => {
  if (timeTrackingInterval) {
    clearInterval(timeTrackingInterval);
    timeTrackingInterval = null;
  }
};

const updateActiveVerseByTime = (chapterId) => {
  if (verseTimeMarkers.value[chapterId] && verseTimeMarkers.value[chapterId].length > 0) {
    let found = false;
    
    for (const marker of verseTimeMarkers.value[chapterId]) {
      if (currentVideoTime.value >= marker.start && currentVideoTime.value < marker.end) {
        if (activeVerseIndex.value !== marker.verseIndex) {
          activeVerseIndex.value = marker.verseIndex;
          highlightedVerseIndex.value = marker.verseIndex;
          
          // Scroll to the verse
          scrollToVerse(marker.verseIndex);
        }
        found = true;
        break;
      }
    }
    
    // If no matching verse found, it could be intro or conclusion
    if (!found) {
      const firstMarker = verseTimeMarkers.value[chapterId][0];
      const lastMarker = verseTimeMarkers.value[chapterId][verseTimeMarkers.value[chapterId].length - 1];
      
      if (firstMarker && currentVideoTime.value < firstMarker.start) {
        // Before first verse
        activeVerseIndex.value = null;
        highlightedVerseIndex.value = null;
      } else if (lastMarker && currentVideoTime.value >= lastMarker.end) {
        // After last verse - keep the last verse active
        activeVerseIndex.value = lastMarker.verseIndex;
        highlightedVerseIndex.value = lastMarker.verseIndex;
      }
    }
  }
};

const loadChapter = async (chapterId) => {
  try {
    console.log('Loading chapter:', chapterId);
    activeChapter.value = chapterId;
    activeVerseIndex.value = null;
    highlightedVerseIndex.value = null;
    playbackInitiated.value = false;
    
    if (!verses.value[chapterId]) {
      const response = await axios.get(`${API_URL.replace(/\/$/, "")}/verses/${chapterId}`);
      console.log('Verses response:', response.data);
      
      if (!response.data || !Array.isArray(response.data)) {
        throw new Error('Invalid verses data received');
      }
      
      verses.value[chapterId] = response.data;
    }
    
    setTimeout(() => {
      initializePlayer(chapterId);
    }, 500);
    
  } catch (error) {
    console.error("Error loading chapter:", error);
    isLoading.value = false;
  }
};

const currentChapter = computed(() => {
  return chapters.value.find(chapter => chapter.chapter_id === activeChapter.value);
});

const currentVerses = computed(() => {
  return verses.value[activeChapter.value] || [];
});

const currentVerse = computed(() => {
  if (activeVerseIndex.value === null || !currentVerses.value[activeVerseIndex.value]) return null;
  return currentVerses.value[activeVerseIndex.value];
});

const isEmptyObj = (obj) => {
  return !obj || Object.keys(obj).length === 0;
};

const playVerse = (verseIndex) => {
  activeVerseIndex.value = verseIndex;
  highlightedVerseIndex.value = verseIndex;
  playbackInitiated.value = true; // Mark that playback has been initiated
  
  // Scroll to the verse
  scrollToVerse(verseIndex);
  
  // Jump the video to that timestamp
  const chapterId = activeChapter.value;
  if (verseTimeMarkers.value[chapterId] && verseTimeMarkers.value[chapterId][verseIndex]) {
    const player = videoPlayers.value[chapterId];
    if (player && typeof player.seekTo === 'function') {
      player.seekTo(verseTimeMarkers.value[chapterId][verseIndex].start);
      player.playVideo();
    }
  }
};

const scrollToVerse = (verseIndex) => {
  // Use setTimeout to ensure DOM has updated
  setTimeout(() => {
    const verseElement = document.getElementById(`verse-${verseIndex}`);
    if (verseElement) {
      verseElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
};



// Check if a verse's interpretation should be highlighted
const isVerseHighlighted = (verseIndex) => {
  return highlightedVerseIndex.value === verseIndex && playbackInitiated.value;
};
</script>

<template>
  <div  class="min-h-screen transition-colors duration-300">
    <!-- Header -->
    <header class="sticky top-0 z-10 bg-gradient-to-r from-amber-600 to-orange-500 dark:from-amber-800 dark:to-orange-700 shadow-lg">
      <div class="container mx-auto flex justify-between items-center p-4">
        <h1 class="text-3xl font-bold text-white">Bhagavad Gita</h1>
        
      
      </div>
    </header>

    <!-- Loading state -->
    <div v-if="isLoading" class="flex items-center justify-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-amber-500"></div>
    </div>

    <div v-else class="bg-amber-50/30 dark:bg-gray-900 min-h-screen">
      <div class="container mx-auto px-4 py-6">
        <!-- Chapter selector -->
        <div class="flex items-center mb-6 overflow-x-auto pb-2 scrollbar-hide">
          <div class="mr-3 text-gray-600 dark:text-gray-300 font-medium shrink-0">Chapter:</div>
          <div class="flex gap-2">
            <button 
              v-for="chapter in chapters" 
              :key="chapter.chapter_id"
              @click="loadChapter(chapter.chapter_id)"
              :class="[
                'px-3 py-2 rounded-lg transition-colors duration-200 text-sm shrink-0',
                activeChapter === chapter.chapter_id 
                  ? 'bg-amber-500 text-white font-medium' 
                  : 'bg-amber-100 text-amber-800 hover:bg-amber-200 dark:bg-amber-900 dark:text-amber-100'
              ]"
            >
              {{ chapter.chapter_id }}
            </button>
          </div>
        </div>

        <!-- Main content -->
        <div v-if="currentChapter" class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <!-- Left sidebar - Chapter info and video -->
          <div class="lg:col-span-4 space-y-6">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-5">
              <h2 class="text-2xl font-bold text-amber-800 dark:text-amber-300 mb-2">
                Chapter {{ currentChapter.chapter_id }}
              </h2>
              <h3 class="text-xl font-medium text-gray-700 dark:text-gray-200 mb-4">
                {{ currentChapter.title }}
              </h3>
              <p class="text-gray-600 dark:text-gray-300">
                {{ currentChapter.description || "No description available" }}
              </p>
            </div>

            <!-- Video player - fixed width on desktop -->
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4 sticky top-20">
              <div class="aspect-w-16 aspect-h-9 rounded-lg overflow-hidden bg-black">
                <div :id="`youtube-player-${currentChapter.chapter_id}`" class="w-full h-full"></div>
              </div>
              <div class="mt-4 flex justify-between items-center">
                <p class="text-gray-700 dark:text-gray-300">
                  <span class="font-medium">Now Playing:</span> 
                  <span v-if="currentVerse">Verse {{ activeVerseIndex + 1 }}</span>
                  <span v-else>Introduction</span>
                </p>
              </div>
            </div>

            <!-- Verse quick navigation -->
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
              <h3 class="text-lg font-medium text-gray-700 dark:text-gray-200 mb-3">
                Jump to Verse
              </h3>
              <div class="flex flex-wrap gap-2">
                <button 
                  v-for="(verse, index) in currentVerses" 
                  :key="index"
                  @click="playVerse(index)"
                  :class="[
                    'px-3 py-1 rounded-md text-sm transition-colors',
                    activeVerseIndex === index 
                      ? 'bg-amber-500 text-white font-medium' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                  ]"
                >
                  {{ index + 1 }}
                </button>
              </div>
            </div>
          </div>

          <!-- Right content - All verses -->
          <div class="lg:col-span-8">
            <div class="space-y-12">
              <div v-for="(verse, index) in currentVerses" :key="index" :id="`verse-${index}`" 
                :class="[
                  'bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 transition-all duration-300',
                  activeVerseIndex === index ? 'ring-2 ring-amber-500' : ''
                ]"
              >
                <div class="mb-6 border-b border-amber-200 dark:border-amber-800 pb-4">
                  <div class="flex justify-between items-center mb-4">
                    <h2 class="text-2xl font-bold text-amber-700 dark:text-amber-400">
                      Verse {{ index + 1 }}
                    </h2>
                    <button 
                      @click="playVerse(index)"
                      class="bg-amber-500 hover:bg-amber-600 text-white text-sm px-3 py-1 rounded"
                    >
                      Play Audio
                    </button>
                  </div>

                  <!-- Sanskrit text -->
                  <div class="mb-6 bg-amber-50 dark:bg-amber-900/40 p-4 rounded-lg text-center">
                    <p class="text-lg text-gray-700 dark:text-gray-200 italic font-bold">
                      <span v-for="(line, lineIndex) in verse.sanskrit_text" :key="lineIndex">
                        {{ line }}<br/>
                      </span>
                    </p>
                  </div>
                </div>

                <!-- Content sections -->
                <div class="space-y-8">
                  <!-- Transliteration -->
                  <div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-xl font-semibold mb-3 text-amber-700 dark:text-amber-400">Transliteration:</h3>
                    <p class="text-lg text-gray-700 dark:text-gray-200">
                      <span v-for="(line, lineIndex) in verse.transliteration" :key="lineIndex">
                        {{ line }}<br/>
                      </span>
                    </p>
                  </div>

                  <!-- Word-by-Word -->
                  <div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-xl font-semibold mb-3 text-amber-700 dark:text-amber-400">Word-by-Word Meaning:</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      <div v-for="(meaning, word, wordIndex) in verse.word_by_word" :key="`${word}-${wordIndex}`" class="bg-white dark:bg-gray-700 p-2 rounded shadow-sm">
                        <strong class="text-amber-800 dark:text-amber-300">{{ word }}:</strong> 
                        <span class="text-gray-700 dark:text-gray-200">{{ meaning }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Translation -->
                  <div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 class="text-xl font-semibold mb-3 text-amber-700 dark:text-amber-400">Translation:</h3>
                    <p class="text-lg text-gray-700 dark:text-gray-200">{{ verse.translation }}</p>
                  </div>

                  <!-- Interpretation - with highlighting when audio is playing -->
                  <div v-if="!isEmptyObj(verse.interpretations)" 
                    :class="[
                      'p-4 rounded-lg transition-all duration-500',
                      isVerseHighlighted(index) 
                        ? 'bg-amber-100 dark:bg-amber-900/50 ring-2 ring-amber-500 shadow-lg transform scale-102' 
                        : 'bg-gray-50 dark:bg-gray-800'
                    ]"
                  >
                    <h3 class="text-xl font-semibold mb-3 text-amber-700 dark:text-amber-400">Interpretations:</h3>
                    <div class="space-y-2">
                      <div v-for="(text, type) in verse.interpretations" :key="type" class="mb-2 p-3 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
                        <h4 class="text-lg font-semibold text-amber-800 dark:text-amber-300 mb-1">{{ type }}:</h4>
                        <p class="text-gray-700 dark:text-gray-200">{{ text }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>