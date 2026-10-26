/* Cinevoryx AI — chat, TMDB discovery, voice and information panels */
const form = document.getElementById('chatForm');
const input = document.getElementById('question');
const sendButton = document.getElementById('sendButton');
const messages = document.getElementById('messages');
const newChatButton = document.getElementById('newChatButton');
const movieSearchForm = document.getElementById('movieSearchForm');
const movieSearchInput = document.getElementById('movieSearchInput');
const movieSearchButton = document.getElementById('movieSearchButton');
const movieSearchStatus = document.getElementById('movieSearchStatus');
const movieGrid = document.getElementById('movieGrid');
const micButton = document.getElementById('micButton');
const speakButton = document.getElementById('speakButton');

let isLoading = false;
let sessionId = crypto.randomUUID();
let lastAnswer = '';
let searchSequence = 0;

function addMessage(text, role) {
  const message = document.createElement('div');
  message.className = `message ${role}`;
  if (role === 'assistant') {
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '✦';
    message.appendChild(avatar);
  }
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text; // Never inject AI or TMDB content as HTML.
  message.appendChild(bubble);
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

async function askCinevoryx(question) {
  if (isLoading || !question || !question.trim()) return;
  const cleanQuestion = question.trim();
  if (cleanQuestion.length > 2000) return;
  isLoading = true;
  sendButton.disabled = true;
  input.disabled = true;
  if (newChatButton) newChatButton.disabled = true;
  addMessage(cleanQuestion, 'user');
  input.value = '';
  const loading = addMessage('Exploring the movie universe...', 'assistant');
  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: cleanQuestion, session_id: sessionId})
    });
    if (!response.ok) throw new Error('The AI service could not complete the request.');
    const data = await response.json();
    if (typeof data.answer !== 'string' || !data.answer.trim()) {
      throw new Error('The server returned an unexpected response.');
    }
    if (typeof data.session_id === 'string') sessionId = data.session_id;
    lastAnswer = data.answer;
    loading.querySelector('.bubble').textContent = lastAnswer;
  } catch (error) {
    console.error('Chat request failed:', error);
    loading.querySelector('.bubble').textContent = error.message || 'Please try again.';
  } finally {
    isLoading = false;
    sendButton.disabled = false;
    input.disabled = false;
    if (newChatButton) newChatButton.disabled = false;
    input.focus();
    messages.scrollTop = messages.scrollHeight;
  }
}

form?.addEventListener('submit', event => {
  event.preventDefault();
  askCinevoryx(input.value);
});
document.querySelectorAll('.suggestion').forEach(button => {
  button.addEventListener('click', () => askCinevoryx(button.dataset.question));
});

// TMDB movie poster gallery
function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = String(text);
  return element;
}
function formatRating(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : 'N/A';
}
function createMovieCard(movie) {
  const card = makeElement('button', 'movie-card');
  card.type = 'button';
  const title = typeof movie.title === 'string' ? movie.title : 'Untitled movie';
  card.setAttribute('aria-label', `View details for ${title}`);
  if (typeof movie.poster_url === 'string' && movie.poster_url.startsWith('https://image.tmdb.org/t/p/')) {
    const img = makeElement('img', 'movie-poster');
    img.src = movie.poster_url;
    img.alt = `Poster for ${title}`;
    img.loading = 'lazy';
    img.referrerPolicy = 'no-referrer';
    card.appendChild(img);
  } else {
    const placeholder = makeElement('div', 'movie-poster movie-poster-placeholder', '🎬 No poster available');
    placeholder.style.display = 'grid';
    placeholder.style.placeItems = 'center';
    card.appendChild(placeholder);
  }
  const body = makeElement('div', 'movie-card-body');
  body.appendChild(makeElement('h3', 'movie-card-title', title));
  const meta = makeElement('div', 'movie-card-meta');
  meta.appendChild(makeElement('span', 'movie-rating', `★ ${formatRating(movie.rating)}`));
  const year = typeof movie.release_date === 'string' ? movie.release_date.slice(0, 4) : '';
  meta.appendChild(makeElement('span', '', year || 'Year unknown'));
  body.appendChild(meta);
  if (movie.overview) body.appendChild(makeElement('p', 'movie-card-overview', movie.overview));
  card.appendChild(body);
  card.addEventListener('click', () => showMovieDetails(movie.id));
  return card;
}

async function searchMoviePosters(query) {
  const searchId = ++searchSequence;
  movieGrid.replaceChildren();
  movieSearchStatus.textContent = 'Searching TMDB...';
  movieSearchButton.disabled = true;
  try {
    const response = await fetch(`/api/movies/search?query=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Movie search is unavailable.');
    const data = await response.json();
    if (searchId !== searchSequence) return;
    const movies = Array.isArray(data.movies) ? data.movies : [];
    movies.forEach(movie => movieGrid.appendChild(createMovieCard(movie)));
    movieSearchStatus.textContent = movies.length
      ? `Showing ${movies.length} movie result${movies.length === 1 ? '' : 's'}. Select a poster for details.`
      : 'No movies found. Try another title.';
  } catch (error) {
    if (searchId === searchSequence) movieSearchStatus.textContent = error.message;
    console.error('TMDB search failed:', error);
  } finally {
    if (searchId === searchSequence) movieSearchButton.disabled = false;
  }
}

async function showMovieDetails(movieId) {
  if (!Number.isInteger(movieId) || movieId <= 0) return;
  movieSearchStatus.textContent = 'Loading movie details...';
  try {
    const response = await fetch(`/api/movies/${movieId}`);
    if (!response.ok) throw new Error('Could not load movie details.');
    const data = await response.json();
    const movie = data.movie;
    if (!movie || typeof movie !== 'object') throw new Error('Invalid movie details.');
    const lines = [
      `🎬 ${movie.title || 'Movie details'}`,
      `⭐ TMDB rating: ${formatRating(movie.rating)}/10`,
      `📅 Release: ${movie.release_date || 'Unknown'}`,
      `⏱ Runtime: ${movie.runtime ? `${movie.runtime} minutes` : 'Unknown'}`,
      `🎭 Genres: ${Array.isArray(movie.genres) ? movie.genres.join(', ') : 'Unknown'}`,
      '',
      movie.overview || 'No description available.'
    ];
    addMessage(lines.join('\n'), 'assistant');
    movieSearchStatus.textContent = 'Movie details added to chat.';
    document.querySelector('.chat-panel')?.scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    movieSearchStatus.textContent = error.message;
  }
}
movieSearchForm?.addEventListener('submit', event => {
  event.preventDefault();
  const query = movieSearchInput.value.trim();
  if (query && query.length <= 200) searchMoviePosters(query);
});

// Browser text-to-speech
const speech = window.speechSynthesis;
if (speakButton) {
  if (!speech) {
    speakButton.disabled = true;
    speakButton.title = 'Speech playback is not supported in this browser';
  } else {
    speakButton.addEventListener('click', () => {
      if (speech.speaking || speech.pending) {
        speech.cancel();
        speakButton.setAttribute('aria-pressed', 'false');
        return;
      }
      if (!lastAnswer) {
        speakButton.title = 'Ask Cinevoryx a question first';
        return;
      }
      const utterance = new SpeechSynthesisUtterance(lastAnswer);
      utterance.lang = 'en-IN';
      utterance.rate = 1;
      utterance.onend = utterance.onerror = () => speakButton.setAttribute('aria-pressed', 'false');
      speakButton.setAttribute('aria-pressed', 'true');
      speech.speak(utterance);
    });
  }
}

// Browser speech-to-text; supported mainly in Chromium browsers.
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (micButton) {
  if (!SpeechRecognition) {
    micButton.disabled = true;
    micButton.title = 'Voice input is not supported in this browser';
  } else {
    recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => {
      micButton.classList.add('is-listening');
      micButton.setAttribute('aria-pressed', 'true');
      micButton.title = 'Listening — click to stop';
    };
    recognition.onend = () => {
      micButton.classList.remove('is-listening');
      micButton.setAttribute('aria-pressed', 'false');
      micButton.title = 'Ask by voice';
    };
    recognition.onerror = event => {
      console.warn('Voice recognition:', event.error);
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        addMessage(`Voice input error: ${event.error}. You can type your question instead.`, 'assistant');
      }
    };
    recognition.onresult = event => {
      const transcript = event.results?.[0]?.[0]?.transcript?.trim();
      if (!transcript) return;
      input.value = transcript;
      if (!isLoading) askCinevoryx(transcript);
    };
    micButton.addEventListener('click', () => {
      if (micButton.classList.contains('is-listening')) recognition.stop();
      else if (!isLoading) {
        try { recognition.start(); }
        catch (error) { console.warn('Could not start microphone:', error); }
      }
    });
  }
}

// New Chat
newChatButton?.addEventListener('click', async () => {
  if (isLoading) return;
  newChatButton.disabled = true;
  try {
    const response = await fetch('/new-chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sessionId})
    });
    if (!response.ok) throw new Error('Could not start a new conversation.');
    const data = await response.json();
    if (typeof data.session_id !== 'string' || !data.session_id) throw new Error('Invalid new session.');
    sessionId = data.session_id;
    lastAnswer = '';
    speech?.cancel();
    recognition?.abort();
    messages.replaceChildren();
    addMessage('New conversation started! What movie would you like to explore?', 'assistant');
    input.focus();
  } catch (error) {
    console.error('New Chat failed:', error);
    alert(error.message);
  } finally {
    newChatButton.disabled = false;
  }
});

// About Developer / About Agent panels
const infoOverlay = document.getElementById('infoOverlay');
const infoPanel = infoOverlay?.querySelector('.info-panel');
const developerInfo = document.getElementById('developerInfo');
const agentInfo = document.getElementById('agentInfo');
const closeInfoButton = document.getElementById('closeInfo');
let previousFocus = null;
function openInfoPanel(type) {
  if (!infoOverlay || !infoPanel || !developerInfo || !agentInfo || !closeInfoButton) return;
  previousFocus = document.activeElement;
  developerInfo.hidden = type !== 'developer';
  agentInfo.hidden = type !== 'agent';
  infoPanel.setAttribute('aria-labelledby', type === 'developer' ? 'infoTitle' : 'agentTitle');
  infoOverlay.hidden = false;
  document.body.style.overflow = 'hidden';
  infoPanel.scrollTop = 0;
  closeInfoButton.focus();
}
function closeInfoPanel() {
  if (!infoOverlay || infoOverlay.hidden) return;
  infoOverlay.hidden = true;
  document.body.style.overflow = '';
  previousFocus?.focus();
}
document.querySelectorAll('[data-panel]').forEach(button => {
  button.addEventListener('click', () => openInfoPanel(button.dataset.panel));
});
closeInfoButton?.addEventListener('click', closeInfoPanel);
infoOverlay?.querySelector('[data-close-panel]')?.addEventListener('click', closeInfoPanel);
document.addEventListener('keydown', event => {
  if (!infoOverlay || infoOverlay.hidden || !infoPanel) return;
  if (event.key === 'Escape') { closeInfoPanel(); return; }
  if (event.key !== 'Tab') return;
  const focusable = Array.from(infoPanel.querySelectorAll(
    'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )).filter(element => !element.disabled && element.getClientRects().length > 0);
  if (!focusable.length) { event.preventDefault(); infoPanel.focus(); return; }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first.focus();
  }
});
