// ── 共享常量与工具函数（student.html / teacher.html 公用） ──────────────

const API = 'http://127.0.0.1:8001';

// ── 网络 ──────────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
    try {
        const res = await fetch(url, options);
        if (res.status === 401) {
            localStorage.removeItem('cqa_user');
            location.href = 'login.html';
            return null;
        }
        return res;
    } catch (err) {
        console.error('Network error:', err);
        throw err;
    }
}

// contentType 传 null/false 可省略 Content-Type（文件上传等场景）
function authHeaders(contentType = 'application/json') {
    const h = { 'Authorization': `Bearer ${user.token}` };
    if (contentType) h['Content-Type'] = contentType;
    return h;
}

function logout() { localStorage.removeItem('cqa_user'); location.href = 'login.html'; }

function displayName(profile) {
    return profile.nickname?.trim() || profile.username;
}

// ── 导航头像/用户名更新（各页面须定义 _navAvatarFallback / _lnavAvatarFallback）────

function applyAvatarToNav(avatar) {
    const navEl  = document.getElementById('nav-avatar');
    const lnavEl = document.getElementById('lnav-avatar');
    if (avatar) {
        const img = `<img src="${avatar}" class="w-full h-full object-cover">`;
        navEl.innerHTML  = img;
        lnavEl.innerHTML = img;
    } else {
        navEl.innerHTML  = _navAvatarFallback;
        lnavEl.innerHTML = _lnavAvatarFallback;
    }
}

function updateNavIdentity(name, avatar) {
    document.getElementById('username-display').textContent = name;
    document.getElementById('lnav-username').textContent    = name;
    applyAvatarToNav(avatar);
}

// ── 图片处理 ──────────────────────────────────────────────────────────────

async function resizeImageToBase64(file, maxSize) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('文件读取失败'));
        reader.onload = e => {
            const img = new Image();
            img.onerror = () => reject(new Error('图片加载失败'));
            img.onload = () => {
                const scale = Math.min(maxSize / img.width, maxSize / img.height, 1);
                const canvas = document.createElement('canvas');
                canvas.width = Math.round(img.width * scale);
                canvas.height = Math.round(img.height * scale);
                canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                resolve(canvas.toDataURL('image/jpeg', 0.85));
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

// ── 个人设置 ──────────────────────────────────────────────────────────────

function closeProfileModal() {
    document.getElementById('modal-profile').classList.add('hidden');
    _pendingAvatar = null;
}

async function changePassword() {
    const current = document.getElementById('pwd-current').value;
    const newPwd = document.getElementById('pwd-new').value;
    const confirm = document.getElementById('pwd-confirm').value;
    const msg = document.getElementById('pwd-msg');
    if (!current || !newPwd) { msg.className = 'text-sm text-red-500'; msg.textContent = '请填写当前密码和新密码'; return; }
    if (newPwd !== confirm) { msg.className = 'text-sm text-red-500'; msg.textContent = '两次输入的新密码不一致'; return; }
    const res = await apiFetch(`${API}/api/auth/password`, {
        method: 'PUT', headers: authHeaders(),
        body: JSON.stringify({ current_password: current, new_password: newPwd })
    });
    if (!res) return;
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        msg.className = 'text-sm text-red-500';
        msg.textContent = err.detail || '修改失败';
        return;
    }
    msg.className = 'text-sm text-green-600';
    msg.textContent = '✅ 密码已更新';
    ['pwd-current','pwd-new','pwd-confirm'].forEach(id => document.getElementById(id).value = '');
}

// ── 导航 ──────────────────────────────────────────────────────────────────

function toggleNavCollapse() {
    _navCollapsed = !_navCollapsed;
    const w = _navCollapsed ? '56px' : '200px';
    document.getElementById('left-nav').style.width = w;
    document.getElementById('main-wrap').style.marginLeft = w;
    document.querySelectorAll('.lnav-label').forEach(el => el.classList.toggle('hidden', _navCollapsed));
    document.getElementById('nav-collapse-icon').style.transform = _navCollapsed ? 'rotate(180deg)' : '';
}

function openSidebar() { navigateTo('msgs'); }

// ── 私信 ──────────────────────────────────────────────────────────────────

function switchMsgsTab(tab) {
    ['private', 'group'].forEach(t => {
        const tabBtn = document.getElementById(`msgs-tab-${t}`);
        if (t === tab) {
            tabBtn.classList.add('border-blue-500', 'text-blue-600');
            tabBtn.classList.remove('border-transparent', 'text-gray-500');
        } else {
            tabBtn.classList.remove('border-blue-500', 'text-blue-600');
            tabBtn.classList.add('border-transparent', 'text-gray-500');
        }
        document.getElementById(`msgs-panel-${t}`)?.classList.toggle('hidden', t !== tab);
    });
    if (tab === 'private') loadConversations();
    else if (tab === 'group') loadGroups();
}

function renderConversations(convs) {
    const listEl = document.getElementById('conversations-list');
    if (!convs.length) { listEl.innerHTML = '<p class="text-gray-400 text-xs text-center py-4">暂无消息记录</p>'; return; }
    listEl.innerHTML = convs.map(c => {
        const name = c.other_nickname?.trim() || c.other_username;
        const dot = c.unread > 0 ? '<span class="w-2 h-2 bg-red-500 rounded-full shrink-0 ml-auto"></span>' : '';
        return `
        <button onclick="openConversation(${c.other_id},'${name.replace(/'/g,'&#39;')}')"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left">
            ${_avatarEl(c.other_avatar, c.other_role)}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1">
                    <p class="text-sm font-medium text-gray-800 truncate">${name}</p>${dot}
                </div>
                <p class="text-xs text-gray-400 truncate">${c.last_content || ''}</p>
            </div>
            <span class="text-xs text-gray-400 shrink-0">${(c.last_at||'').slice(5,16)}</span>
        </button>`;
    }).join('');
}

function openConversation(userId, userName) {
    _currentConvUserId = userId;
    _currentConvUserName = userName;
    document.getElementById('conv-placeholder')?.classList.add('hidden');
    document.getElementById('conv-detail-view').classList.remove('hidden');
    document.getElementById('conv-partner-name').textContent = userName;
    document.getElementById('conv-messages').innerHTML = '<p class="text-gray-400 text-xs text-center py-4">加载中...</p>';
    closeConvMenu();
    loadConvMessages();
    loadPinnedMsg();
}

function backToConversations() {
    _currentConvUserId = null;
    _currentConvUserName = null;
    document.getElementById('conv-detail-view').classList.add('hidden');
    document.getElementById('conv-placeholder')?.classList.remove('hidden');
}

async function loadConvMessages() {
    if (!_currentConvUserId) return;
    try {
        // 先获取消息（服务端同时标为已读），再查未读数，避免并发竞争
        const res = await apiFetch(`${API}/api/messages/conversation/${_currentConvUserId}`, { headers: authHeaders() });
        if (res) renderConvMessages(await res.json());
        const [r1, r2] = await Promise.all([
            apiFetch(`${API}/api/messages/unread-count`, { headers: authHeaders() }),
            apiFetch(`${API}/api/groups/unread-total`, { headers: authHeaders() }),
        ]);
        const privateCount = r1 ? (await r1.json()).count : 0;
        const groupCount   = r2 ? (await r2.json()).count : 0;
        updateUnreadBadge(privateCount, groupCount);
        loadConversations();
    } catch {}
}

function renderConvMessages(msgs) {
    const el = document.getElementById('conv-messages');
    if (!msgs.length) { el.innerHTML = '<p class="text-gray-400 text-xs text-center py-4">还没有消息，发送第一条吧</p>'; return; }
    el.innerHTML = msgs.map(m => {
        const isMine = m.sender_id !== _currentConvUserId;
        const escaped = String(m.content).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        if (isMine) {
            return `
            <div class="flex group justify-end items-end gap-1">
                <button onclick="pinMessage(${m.id})" class="mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-amber-500 text-xs shrink-0 order-first" title="置顶">📌</button>
                <div class="max-w-[75%] bg-blue-600 text-white rounded-2xl px-4 py-2 text-sm">
                    <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                    <p class="text-xs mt-1 text-blue-200">${(m.created_at||'').slice(5,16)}</p>
                </div>
            </div>`;
        }
        return `
        <div class="flex group justify-start items-end gap-2">
            ${_avatarEl(m.sender_avatar, m.sender_role, 'w-8 h-8', 'text-xs')}
            <div class="flex items-end gap-1">
                <div class="max-w-[75%] bg-gray-100 text-gray-800 rounded-2xl px-4 py-2 text-sm">
                    <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                    <p class="text-xs mt-1 text-gray-400">${(m.created_at||'').slice(5,16)}</p>
                </div>
                <button onclick="pinMessage(${m.id})" class="mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-amber-500 text-xs shrink-0" title="置顶">📌</button>
            </div>
        </div>`;
    }).join('');
    el.scrollTop = el.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('msg-input');
    const content = input.value.trim();
    if (!content || !_currentConvUserId) return;
    input.value = '';
    try {
        await apiFetch(`${API}/api/messages`, {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ receiver_id: _currentConvUserId, content })
        });
        loadConvMessages();
    } catch {}
}

async function startMsgPoll() {
    stopMsgPoll();
    const check = async () => {
        try {
            const [r1, r2] = await Promise.all([
                apiFetch(`${API}/api/messages/unread-count`, { headers: authHeaders() }),
                apiFetch(`${API}/api/groups/unread-total`, { headers: authHeaders() }),
            ]);
            const privateCount = r1 ? (await r1.json()).count : 0;
            const groupCount   = r2 ? (await r2.json()).count : 0;
            const total = privateCount + groupCount;
            if (total !== _lastUnreadCount) { _lastUnreadCount = total; updateUnreadBadge(privateCount, groupCount); }
        } catch {}
    };
    await check();
    _msgPollTimer = setInterval(check, 30000);
}

function stopMsgPoll() {
    if (_msgPollTimer) { clearInterval(_msgPollTimer); _msgPollTimer = null; }
}

function setBadge(el, count) {
    if (!el) return;
    el.textContent = count > 9 ? '9+' : count;
    el.classList.toggle('hidden', count === 0);
}

function updateUnreadBadge(privateCount, groupCount) {
    if (groupCount === undefined) { groupCount = 0; }
    setBadge(document.getElementById('msg-badge'), privateCount + groupCount);
    setBadge(document.getElementById('msgs-private-badge'), privateCount);
    setBadge(document.getElementById('msgs-group-badge'), groupCount);
}

// ── 头像辅助 ──────────────────────────────────────────────────────────────

function _avatarEl(src, role, sizeClass = 'w-9 h-9', textClass = 'text-sm') {
    if (src) return `<img src="${src}" class="${sizeClass} rounded-full object-cover shrink-0 border border-gray-100">`;
    const isTeacher = role === 'teacher';
    const bg   = isTeacher ? 'bg-blue-100 text-blue-500' : 'bg-green-100 text-green-500';
    const icon = isTeacher ? 'fa-chalkboard-teacher' : 'fa-user-graduate';
    return `<div class="${sizeClass} ${bg} rounded-full flex items-center justify-center shrink-0 ${textClass}"><i class="fas ${icon}"></i></div>`;
}

// ── 笔记通用 ──────────────────────────────────────────────────────────────

const NOTE_COLORS = ['from-blue-400 to-indigo-500','from-green-400 to-teal-500','from-amber-400 to-orange-500','from-purple-400 to-pink-500','from-rose-400 to-red-500'];

function closeCourseFilterModal() {
    document.getElementById('modal-course-filter')?.classList.add('hidden');
}

// ── 设置页 ────────────────────────────────────────────────────────────────

function switchSettingsTab(tab) {
    ['basic', 'account', 'theme'].forEach(t => {
        document.getElementById(`settings-content-${t}`)?.classList.toggle('hidden', t !== tab);
        const btn = document.getElementById(`settings-tab-${t}`);
        if (!btn) return;
        btn.className = 'flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ' +
            (t === tab ? _settingsTabActiveClass : 'text-gray-600 hover:bg-gray-50');
    });
    if (tab === 'theme') {
        if (typeof renderThemeSwatches === 'function') renderThemeSwatches();
        if (typeof renderDarkToggle === 'function') renderDarkToggle();
    }
}

function loadSettingsPage() {
    const idEl = document.getElementById('settings-user-id');
    if (idEl) idEl.textContent = userProfile.id || '-';
    const genderEl = document.getElementById('settings-gender');
    if (genderEl) genderEl.value = userProfile.gender || '';
    const phoneEl = document.getElementById('settings-phone');
    if (phoneEl) phoneEl.value = userProfile.phone || '';
    const basicMsg = document.getElementById('settings-basic-msg');
    if (basicMsg) basicMsg.textContent = '';
    ['pwd-current','pwd-new','pwd-confirm'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const pwdMsg = document.getElementById('pwd-msg');
    if (pwdMsg) pwdMsg.textContent = '';
    switchSettingsTab('basic');
}

async function saveBasicInfo() {
    const gender = document.getElementById('settings-gender')?.value || null;
    const phone = document.getElementById('settings-phone')?.value.trim() || null;
    const msg = document.getElementById('settings-basic-msg');
    const res = await apiFetch(`${API}/api/auth/basic-info`, {
        method: 'PUT', headers: authHeaders(),
        body: JSON.stringify({ gender, phone })
    });
    if (!res) return;
    if (!res.ok) {
        if (msg) { msg.className = 'text-sm text-red-500 min-h-[20px]'; msg.textContent = '保存失败'; }
        return;
    }
    userProfile.gender = gender;
    userProfile.phone = phone;
    if (msg) {
        msg.className = 'text-sm text-green-600 min-h-[20px]';
        msg.textContent = '✅ 已保存';
        setTimeout(() => { msg.textContent = ''; }, 2000);
    }
}

// ── 主题 ──────────────────────────────────────────────────────────────────

const _settingsTabActiveClass = 'bg-blue-600 text-white';

const THEMES = [
    { name: 'default', label: '默认蓝', bg: '#2563eb' },
    { name: 'orange',  label: '暖橙',   bg: '#ea580c' },
    { name: 'rose',    label: '玫红',   bg: '#e11d48' },
    { name: 'teal',    label: '青绿',   bg: '#0d9488' },
    { name: 'purple',  label: '紫色',   bg: '#7c3aed' },
    { name: 'sky',     label: '天蓝',   bg: '#0284c7' },
    { name: 'amber',   label: '金黄',   bg: '#d97706' },
    { name: 'indigo',  label: '靛蓝',   bg: '#4f46e5' },
    { name: 'pink',    label: '粉红',   bg: '#db2777' },
    { name: 'lime',    label: '青柠',   bg: '#65a30d' },
];

function renderDarkToggle() {
    const btn = document.getElementById('dark-toggle-btn');
    if (!btn) return;
    const isDark = getSavedDark();
    btn.classList.toggle('bg-blue-600', isDark);
    btn.classList.toggle('bg-gray-200', !isDark);
    const thumb = btn.querySelector('[data-thumb]');
    if (thumb) thumb.style.transform = isDark ? 'translateX(1.25rem)' : '';
}

function renderThemeSwatches() {
    const current = getSavedTheme();
    const el = document.getElementById('theme-swatches');
    if (!el) return;
    el.innerHTML = THEMES.map(t => `
        <div onclick="applyTheme('${t.name}')" class="flex flex-col items-center gap-2 cursor-pointer group">
            <div class="w-12 h-12 rounded-2xl shadow-sm transition-transform group-hover:scale-110 flex items-center justify-center ${current === t.name ? 'ring-2 ring-offset-2 ring-gray-500' : ''}"
                style="background:${t.bg}">
                ${current === t.name ? '<i class="fas fa-check text-white text-sm"></i>' : ''}
            </div>
            <span class="text-xs text-gray-500 font-medium">${t.label}</span>
        </div>`).join('');
}

function toggleDarkMode() {
    const nowDark = !getSavedDark();
    nowDark ? document.body.setAttribute('data-dark', '1') : document.body.removeAttribute('data-dark');
    localStorage.setItem('cqa_dark', nowDark ? '1' : '0');
    if (typeof renderDarkToggle === 'function') renderDarkToggle();
}

function getSavedDark() { return localStorage.getItem('cqa_dark') === '1'; }

function loadSavedDark() { if (getSavedDark()) document.body.setAttribute('data-dark', '1'); }

function applyTheme(name) {
    if (name === 'default') {
        document.body.removeAttribute('data-theme');
    } else {
        document.body.setAttribute('data-theme', name);
    }
    localStorage.setItem('cqa_theme', name);
    if (typeof renderThemeSwatches === 'function') renderThemeSwatches();
}

function getSavedTheme() {
    return localStorage.getItem('cqa_theme') || 'default';
}

function loadSavedTheme() {
    const theme = getSavedTheme();
    if (theme !== 'default') document.body.setAttribute('data-theme', theme);
}

// ── 私聊三点菜单 ──────────────────────────────────────────────────────────────

function toggleConvMenu() {
    const dd = document.getElementById('conv-menu-dropdown');
    dd.classList.toggle('hidden');
}

function closeConvMenu() {
    document.getElementById('conv-menu-dropdown')?.classList.add('hidden');
}

// ── 对方个人信息 ──────────────────────────────────────────────────────────────

async function openPartnerProfile() {
    closeConvMenu();
    if (!_currentConvUserId) return;
    const modal = document.getElementById('modal-partner-profile');
    const content = document.getElementById('partner-profile-content');
    content.innerHTML = '<p class="text-gray-400 text-center">加载中...</p>';
    modal.classList.remove('hidden');
    try {
        const res = await apiFetch(`${API}/api/auth/users/${_currentConvUserId}/profile`, { headers: authHeaders() });
        if (!res || !res.ok) { content.innerHTML = '<p class="text-red-500 text-center">加载失败</p>'; return; }
        const p = await res.json();
        const genderMap = { male: '男', female: '女', other: '其他' };
        const roleMap = { teacher: '教师', student: '学生' };
        const avatarHtml = p.avatar
            ? `<img src="${p.avatar}" class="w-14 h-14 rounded-full object-cover mb-2">`
            : `<div class="w-14 h-14 rounded-full ${p.role==='teacher'?'bg-blue-100 text-blue-500':'bg-green-100 text-green-500'} flex items-center justify-center text-2xl mb-2"><i class="fas ${p.role==='teacher'?'fa-chalkboard-teacher':'fa-user-graduate'}"></i></div>`;
        content.innerHTML = `
            <div class="flex flex-col items-center mb-4">
                ${avatarHtml}
                <p class="font-semibold text-gray-800">${p.nickname?.trim() || p.username}</p>
                <p class="text-xs text-gray-400">${roleMap[p.role] || p.role}</p>
            </div>
            <div class="space-y-2 text-sm">
                <div class="flex justify-between py-1.5 border-b border-gray-100">
                    <span class="text-gray-500">用户名</span><span class="text-gray-800">${p.username}</span>
                </div>
                <div class="flex justify-between py-1.5 border-b border-gray-100">
                    <span class="text-gray-500">性别</span><span class="text-gray-800">${genderMap[p.gender] || '未填写'}</span>
                </div>
                <div class="flex justify-between py-1.5">
                    <span class="text-gray-500">联系方式</span><span class="text-gray-800">${p.phone || '未填写'}</span>
                </div>
            </div>`;
    } catch { content.innerHTML = '<p class="text-red-500 text-center">连接失败</p>'; }
}

function closePartnerProfile() {
    document.getElementById('modal-partner-profile').classList.add('hidden');
}

// ── 私聊置顶消息 ──────────────────────────────────────────────────────────────

async function loadPinnedMsg() {
    if (!_currentConvUserId) return;
    try {
        const res = await apiFetch(`${API}/api/messages/conversation/${_currentConvUserId}/pin`, { headers: authHeaders() });
        if (!res) return;
        renderPinnedBanner(res.ok ? await res.json() : null);
    } catch {}
}

function renderPinnedBanner(pin) {
    const banner = document.getElementById('conv-pin-banner');
    const text   = document.getElementById('conv-pin-text');
    if (!banner) return;
    if (!pin) { banner.classList.add('hidden'); return; }
    const preview = String(pin.content || '').replace(/\n/g, ' ').slice(0, 60);
    text.textContent = preview + (pin.content?.length > 60 ? '…' : '');
    banner.classList.remove('hidden');
}

async function pinMessage(msgId) {
    if (!_currentConvUserId) return;
    try {
        await apiFetch(`${API}/api/messages/conversation/${_currentConvUserId}/pin`, {
            method: 'PUT', headers: authHeaders(),
            body: JSON.stringify({ message_id: msgId }),
        });
        loadPinnedMsg();
    } catch {}
}

async function unpinMessage() {
    if (!_currentConvUserId) return;
    try {
        await apiFetch(`${API}/api/messages/conversation/${_currentConvUserId}/pin`, {
            method: 'DELETE', headers: authHeaders(),
        });
        renderPinnedBanner(null);
    } catch {}
}

// ── 历史聊天（日历弹窗）────────────────────────────────────────────────────────

let _historyDates = [];
let _historyYear  = null;
let _historyMonth = null;
let _historyMode  = 'private';   // 'private' | 'group'

async function openHistoryPicker() {
    closeConvMenu();
    _historyMode = 'private';
    _historyDates = [];
    document.getElementById('history-date-msgs').innerHTML = '<p class="text-center py-4 text-xs text-gray-400">点击有消息的日期查看记录</p>';
    document.getElementById('modal-history-picker').classList.remove('hidden');
    if (!_currentConvUserId) return;
    try {
        const res = await apiFetch(`${API}/api/messages/conversation/${_currentConvUserId}/dates`, { headers: authHeaders() });
        if (res && res.ok) _historyDates = await res.json();
    } catch {}
    const now = new Date();
    _historyYear  = now.getFullYear();
    _historyMonth = now.getMonth() + 1;
    renderHistoryCalendar();
}

async function openGroupHistoryPicker() {
    closeGroupMenu();
    _historyMode  = 'group';
    _historyDates = [];
    document.getElementById('history-date-msgs').innerHTML = '<p class="text-center py-4 text-xs text-gray-400">点击有消息的日期查看记录</p>';
    document.getElementById('modal-history-picker').classList.remove('hidden');
    if (!_currentGroupId) return;
    try {
        const res = await apiFetch(`${API}/api/groups/${_currentGroupId}/dates`, { headers: authHeaders() });
        if (res && res.ok) _historyDates = await res.json();
    } catch {}
    const now = new Date();
    _historyYear  = now.getFullYear();
    _historyMonth = now.getMonth() + 1;
    renderHistoryCalendar();
}

function closeHistoryPicker() {
    document.getElementById('modal-history-picker').classList.add('hidden');
}

function renderHistoryCalendar() {
    const label = document.getElementById('history-month-label');
    const grid  = document.getElementById('history-calendar-grid');
    if (!label || !grid) return;
    label.textContent = `${_historyYear} 年 ${_historyMonth} 月`;

    const dateSet = new Set(_historyDates);
    const firstDay = new Date(_historyYear, _historyMonth - 1, 1).getDay();
    const daysInMonth = new Date(_historyYear, _historyMonth, 0).getDate();

    let html = ['日','一','二','三','四','五','六'].map(d =>
        `<div class="py-1 text-gray-400 font-medium">${d}</div>`
    ).join('');

    for (let i = 0; i < firstDay; i++) html += '<div></div>';
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${_historyYear}-${String(_historyMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const hasMsg  = dateSet.has(dateStr);
        html += `<button onclick="pickHistoryDate('${dateStr}')"
            class="py-1 rounded-lg text-sm ${hasMsg ? 'bg-blue-100 text-blue-700 font-semibold hover:bg-blue-200' : 'text-gray-400 cursor-default'}"
            ${hasMsg ? '' : 'disabled'}>${d}</button>`;
    }
    grid.innerHTML = html;
}

function prevHistoryMonth() {
    _historyMonth--;
    if (_historyMonth < 1) { _historyMonth = 12; _historyYear--; }
    renderHistoryCalendar();
}

function nextHistoryMonth() {
    _historyMonth++;
    if (_historyMonth > 12) { _historyMonth = 1; _historyYear++; }
    renderHistoryCalendar();
}

async function pickHistoryDate(dateStr) {
    const el = document.getElementById('history-date-msgs');
    el.innerHTML = '<p class="text-center py-4 text-xs text-gray-400">加载中...</p>';
    try {
        let url;
        if (_historyMode === 'private') {
            url = `${API}/api/messages/conversation/${_currentConvUserId}/history?date=${dateStr}`;
        } else {
            url = `${API}/api/groups/${_currentGroupId}/messages?date=${dateStr}`;
        }
        const res = await apiFetch(url, { headers: authHeaders() });
        if (!res || !res.ok) { el.innerHTML = '<p class="text-center py-2 text-xs text-red-400">加载失败</p>'; return; }
        const msgs = await res.json();
        if (!msgs.length) { el.innerHTML = `<p class="text-center py-4 text-xs text-gray-400">${dateStr} 无消息记录</p>`; return; }

        if (_historyMode === 'private') {
            el.innerHTML = msgs.map(m => {
                const isMine = m.sender_id !== _currentConvUserId;
                const escaped = String(m.content).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                return `<div class="flex ${isMine?'justify-end':'justify-start'} mb-2">
                    <div class="max-w-[85%] ${isMine?'bg-blue-100 text-blue-800':'bg-gray-100 text-gray-800'} rounded-xl px-3 py-1.5 text-xs">
                        <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                        <p class="text-[10px] mt-0.5 text-gray-400">${(m.created_at||'').slice(11,16)}</p>
                    </div>
                </div>`;
            }).join('');
        } else {
            el.innerHTML = msgs.map(m => {
                const name = m.sender_nickname?.trim() || m.sender_username;
                const escaped = String(m.content).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                return `<div class="mb-2">
                    <p class="text-[10px] text-gray-400 mb-0.5">${name} · ${(m.created_at||'').slice(11,16)}</p>
                    <div class="bg-gray-100 text-gray-800 rounded-xl px-3 py-1.5 text-xs inline-block max-w-[85%]">
                        <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                    </div>
                </div>`;
            }).join('');
        }
    } catch { el.innerHTML = '<p class="text-center py-2 text-xs text-red-400">连接失败</p>'; }
}

// ── 群组聊天 ──────────────────────────────────────────────────────────────────

async function loadGroups() {
    const listEl = document.getElementById('groups-list');
    if (!listEl) return;
    listEl.innerHTML = '<p class="text-gray-400 text-xs text-center py-4">加载中...</p>';
    try {
        const res = await apiFetch(`${API}/api/groups`, { headers: authHeaders() });
        if (!res) return;
        renderGroups(await res.json());
    } catch {}
}

function renderGroups(groups) {
    const listEl = document.getElementById('groups-list');
    if (!listEl) return;
    if (!groups.length) { listEl.innerHTML = '<p class="text-gray-400 text-xs text-center py-4">暂未加入任何群组</p>'; return; }
    listEl.innerHTML = groups.map(g => {
        const dot = g.unread > 0 ? `<span class="min-w-[16px] h-4 bg-red-500 text-white text-[9px] font-bold rounded-full inline-flex items-center justify-center px-1 ml-auto">${g.unread > 9 ? '9+' : g.unread}</span>` : '';
        return `
        <button onclick="openGroup(${g.id},'${String(g.name).replace(/'/g,'&#39;')}')"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 text-left">
            <div class="w-9 h-9 bg-indigo-100 text-indigo-500 rounded-full flex items-center justify-center shrink-0 text-sm">
                <i class="fas fa-users"></i>
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1">
                    <p class="text-sm font-medium text-gray-800 truncate">${g.name}</p>${dot}
                </div>
                <p class="text-xs text-gray-400 truncate">${g.last_content || '暂无消息'}</p>
            </div>
            <span class="text-xs text-gray-400 shrink-0">${(g.last_at||'').slice(5,16)}</span>
        </button>`;
    }).join('');
}

function openGroup(groupId, groupName) {
    _currentGroupId   = groupId;
    _currentGroupName = groupName;
    document.getElementById('group-placeholder')?.classList.add('hidden');
    document.getElementById('group-detail-view').classList.remove('hidden');
    document.getElementById('group-name').textContent = groupName;
    document.getElementById('group-messages').innerHTML = '<p class="text-gray-400 text-xs text-center py-4">加载中...</p>';
    document.getElementById('group-pin-banners')?.innerHTML && (document.getElementById('group-pin-banners').innerHTML = '');
    closeGroupMenu();
    loadGroupMessages();
    loadGroupPins();
}

function backToGroups() {
    _currentGroupId   = null;
    _currentGroupName = null;
    document.getElementById('group-detail-view').classList.add('hidden');
    document.getElementById('group-placeholder')?.classList.remove('hidden');
}

async function loadGroupMessages(date) {
    if (!_currentGroupId) return;
    let url = `${API}/api/groups/${_currentGroupId}/messages`;
    if (date) url += `?date=${date}`;
    try {
        const res = await apiFetch(url, { headers: authHeaders() });
        if (res) renderGroupMessages(await res.json());
    } catch {}
}

function renderGroupMessages(msgs) {
    const el = document.getElementById('group-messages');
    if (!el) return;
    if (!msgs.length) { el.innerHTML = '<p class="text-gray-400 text-xs text-center py-4">还没有消息，发送第一条吧</p>'; return; }
    el.innerHTML = msgs.map(m => {
        const isMine = m.sender_id === user.id;
        const name   = m.sender_nickname?.trim() || m.sender_username;
        const escaped = String(m.content).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        if (isMine) {
            return `
            <div class="flex justify-end">
                <div class="max-w-[75%] bg-blue-600 text-white rounded-2xl px-4 py-2 text-sm">
                    <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                    <p class="text-xs mt-1 text-blue-200">${(m.created_at||'').slice(5,16)}</p>
                </div>
            </div>`;
        }
        const canPin = typeof user !== 'undefined' && user.role === 'teacher';
        return `
        <div class="flex group justify-start gap-2 items-end">
            ${_avatarEl(m.sender_avatar, m.sender_role, 'w-8 h-8 shrink-0', 'text-xs')}
            <div class="max-w-[70%]">
                <p class="text-xs text-gray-400 mb-0.5">${name}</p>
                <div class="flex items-end gap-1">
                    <div class="bg-gray-100 text-gray-800 rounded-2xl px-4 py-2 text-sm">
                        <p style="white-space:pre-wrap;word-break:break-word">${escaped}</p>
                        <p class="text-xs mt-1 text-gray-400">${(m.created_at||'').slice(5,16)}</p>
                    </div>
                    ${canPin ? `<button onclick="pinGroupMessage(${m.id})" class="mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-amber-500 text-xs shrink-0" title="置顶">📌</button>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');
    el.scrollTop = el.scrollHeight;
}

async function sendGroupMessage() {
    const input = document.getElementById('group-msg-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content || !_currentGroupId) return;
    input.value = '';
    input.style.height = 'auto';
    try {
        await apiFetch(`${API}/api/groups/${_currentGroupId}/messages`, {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ content }),
        });
        loadGroupMessages();
    } catch {}
}

// ── 群组三点菜单 ──────────────────────────────────────────────────────────────

function toggleGroupMenu() {
    document.getElementById('group-menu-dropdown')?.classList.toggle('hidden');
}

function closeGroupMenu() {
    document.getElementById('group-menu-dropdown')?.classList.add('hidden');
}

// ── 群组置顶 ──────────────────────────────────────────────────────────────────

async function loadGroupPins() {
    if (!_currentGroupId) return;
    try {
        const res = await apiFetch(`${API}/api/groups/${_currentGroupId}/pins`, { headers: authHeaders() });
        if (res && res.ok) renderGroupPinBanners(await res.json());
    } catch {}
}

function renderGroupPinBanners(pins) {
    const el = document.getElementById('group-pin-banners');
    if (!el) return;
    if (!pins || !pins.length) { el.innerHTML = ''; return; }
    const isTeacher = typeof user !== 'undefined' && user.role === 'teacher';
    el.innerHTML = pins.map(p => {
        const preview = String(p.content || '').replace(/\n/g, ' ').slice(0, 60);
        const pinner  = p.pinner_nickname?.trim() || p.pinner_name;
        const unpinBtn = isTeacher
            ? `<button onclick="unpinGroupMessage(${p.message_id})" class="text-gray-400 hover:text-gray-600 text-xs shrink-0 ml-2">取消</button>`
            : '';
        return `<div class="flex items-center gap-2 px-4 py-1.5 bg-amber-50 border-b border-amber-100 text-xs">
            <i class="fas fa-thumbtack text-amber-500 text-[10px] shrink-0"></i>
            <span class="text-gray-500 shrink-0">由 ${pinner} 置顶</span>
            <span class="flex-1 truncate text-gray-700">${preview}${p.content?.length > 60 ? '…' : ''}</span>
            ${unpinBtn}
        </div>`;
    }).join('');
}

async function pinGroupMessage(msgId) {
    if (!_currentGroupId) return;
    try {
        await apiFetch(`${API}/api/groups/${_currentGroupId}/pins`, {
            method: 'PUT', headers: authHeaders(),
            body: JSON.stringify({ message_id: msgId }),
        });
        loadGroupPins();
    } catch {}
}

async function unpinGroupMessage(msgId) {
    if (!_currentGroupId) return;
    try {
        await apiFetch(`${API}/api/groups/${_currentGroupId}/pins/${msgId}`, {
            method: 'DELETE', headers: authHeaders(),
        });
        loadGroupPins();
    } catch {}
}

// ── 群成员列表 ────────────────────────────────────────────────────────────────

async function openGroupMembersList() {
    closeGroupMenu();
    if (!_currentGroupId) return;
    const modal = document.getElementById('modal-group-members');
    const content = document.getElementById('group-members-content');
    if (!modal) return;
    content.innerHTML = '<p class="text-gray-400 text-center text-sm py-4">加载中...</p>';
    modal.classList.remove('hidden');
    try {
        const res = await apiFetch(`${API}/api/groups/${_currentGroupId}/members`, { headers: authHeaders() });
        if (!res || !res.ok) { content.innerHTML = '<p class="text-red-500 text-center text-sm py-4">加载失败</p>'; return; }
        const members = await res.json();
        if (!members.length) { content.innerHTML = '<p class="text-gray-400 text-center text-sm py-4">暂无成员</p>'; return; }
        const teachers = members.filter(m => m.role === 'teacher');
        const students = members.filter(m => m.role === 'student');
        const renderSection = (list, label) => {
            if (!list.length) return '';
            return `<div class="mb-3">
                <p class="text-xs text-gray-400 font-medium mb-2 px-1">${label}（${list.length}）</p>
                ${list.map(m => {
                    const name = m.nickname?.trim() || m.username;
                    const avatar = _avatarEl(m.avatar, m.role, 'w-9 h-9', 'text-sm');
                    return `<div class="flex items-center gap-3 py-2.5 px-1 rounded-xl hover:bg-gray-50">
                        ${avatar}
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium text-gray-800 truncate">${name}</p>
                            <p class="text-xs text-gray-400">@${m.username}</p>
                        </div>
                        <span class="text-xs text-gray-400">${(m.joined_at||'').slice(5,10)}</span>
                    </div>`;
                }).join('')}
            </div>`;
        };
        content.innerHTML = renderSection(teachers, '教师') + renderSection(students, '学生');
    } catch { content.innerHTML = '<p class="text-red-500 text-center text-sm py-4">连接失败</p>'; }
}

function closeGroupMembersList() {
    document.getElementById('modal-group-members')?.classList.add('hidden');
}

// ── 日历 ─────────────────────────────────────────────────────────────────────

let _calYear = new Date().getFullYear();
let _calMonth = new Date().getMonth() + 1; // 1-12
let _calDots = {}; // {"YYYY-MM-DD": {blue, red, unread}}

function initCalendar() {
    _calYear = new Date().getFullYear();
    _calMonth = new Date().getMonth() + 1;
    fetchCalendarDots().then(() => renderCalendar(true));
}

function refreshCalendar() {
    fetchCalendarDots().then(() => renderCalendar());
}

async function fetchCalendarDots() {
    try {
        const res = await apiFetch(
            `${API}/api/schedules/dots?year=${_calYear}&month=${_calMonth}`,
            { headers: authHeaders() }
        );
        if (!res) return;
        _calDots = await res.json();
    } catch { _calDots = {}; }
}

function prevCalMonth() {
    if (--_calMonth < 1) { _calMonth = 12; _calYear--; }
    fetchCalendarDots().then(() => renderCalendar());
}

function nextCalMonth() {
    if (++_calMonth > 12) { _calMonth = 1; _calYear++; }
    fetchCalendarDots().then(() => renderCalendar());
}

function renderCalendar(scrollToToday = false) {
    const label = document.getElementById('cal-month-label');
    const grid = document.getElementById('cal-grid');
    if (!label || !grid) return;
    label.textContent = `${_calYear}年${_calMonth}月`;

    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
    const daysInMonth = new Date(_calYear, _calMonth, 0).getDate();
    const WEEKDAYS = ['周日','周一','周二','周三','周四','周五','周六'];

    const rows = [];
    for (let d = 1; d <= daysInMonth; d++) {
        const ds = `${_calYear}-${String(_calMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const isToday = ds === todayStr;
        const isPast = ds < todayStr;
        const weekday = WEEKDAYS[new Date(_calYear, _calMonth - 1, d).getDay()];
        rows.push(_calRow(d, ds, weekday, isToday, isPast));
    }

    grid.innerHTML = rows.join('');
    if (scrollToToday) _scrollCalToToday();
}

function _calRow(day, dateStr, weekday, isToday, isPast) {
    const dots = _calDots[dateStr] || {};
    const hasUnread = !isPast && dots.unread;
    const blueCount = dots.blue_count || 0;
    const redCount = dots.red_count || 0;

    const bgCls = hasUnread ? 'bg-red-50' : '';
    const hoverCls = hasUnread ? 'hover:bg-red-100' : 'hover:bg-gray-100';
    const weekdayCls = isPast ? 'text-gray-300' : 'text-gray-400';
    const numCls = isToday
        ? 'bg-blue-600 text-white rounded-full'
        : isPast ? 'text-gray-300' : 'text-gray-700';

    let badgeHtml = '';
    if (redCount > 0) badgeHtml += `<span class="px-1 py-0.5 bg-red-500 text-white text-[9px] font-bold leading-none rounded">${redCount}</span>`;
    if (blueCount > 0) badgeHtml += `<span class="px-1 py-0.5 bg-blue-500 text-white text-[9px] font-bold leading-none rounded">${blueCount}</span>`;

    const todayId = isToday ? 'id="cal-today-row"' : '';

    return `<div class="flex items-center px-3 py-2 rounded-lg ${bgCls} ${hoverCls} cursor-pointer transition-colors" ondblclick="onDateDblClick('${dateStr}')" ${todayId}>
        <span class="text-xs ${weekdayCls} w-8 shrink-0">${weekday}</span>
        <span class="w-7 h-7 flex items-center justify-center text-sm font-medium ${numCls}">${day}</span>
        <div class="flex gap-1 ml-auto items-center">${badgeHtml}</div>
    </div>`;
}

function _scrollCalToToday() {
    const sidebar = document.getElementById('cal-sidebar');
    const todayRow = document.getElementById('cal-today-row');
    if (!sidebar || !todayRow) return;
    const headerEl = sidebar.querySelector('.cal-sticky-header');
    const headerH = headerEl ? headerEl.offsetHeight : 0;
    const sidebarRect = sidebar.getBoundingClientRect();
    const rowRect = todayRow.getBoundingClientRect();
    const rowTopRelative = rowRect.top - sidebarRect.top + sidebar.scrollTop;
    const visH = sidebar.clientHeight - headerH;
    sidebar.scrollTop = rowTopRelative - headerH - visH / 2 + todayRow.offsetHeight / 2;
}

function onDateDblClick(dateStr) {
    openScheduleModal(dateStr);
}

// ── 日程弹窗 ─────────────────────────────────────────────────────────────────

let _scheduleDate = '';
let _editingScheduleId = null;
let _schedOrigTitle = '';
let _schedOrigContent = '';

async function openScheduleModal(dateStr) {
    _scheduleDate = dateStr;
    const [y, m, d] = dateStr.split('-').map(Number);
    document.getElementById('schedule-modal-title').textContent = `${y}年${m}月${d}日`;

    const todayStr = new Date().toISOString().slice(0, 10);
    const addBtn = document.getElementById('sched-add-btn');
    if (addBtn) addBtn.classList.toggle('hidden', dateStr < todayStr);

    document.getElementById('modal-schedule-day').classList.remove('hidden');
    await loadDaySchedules();
}

function closeScheduleModal() {
    document.getElementById('modal-schedule-day').classList.add('hidden');
}

async function loadDaySchedules() {
    const content = document.getElementById('schedule-day-content');
    content.innerHTML = '<p class="text-center text-gray-400 text-sm py-8">加载中...</p>';
    const [y, m] = _scheduleDate.split('-');
    try {
        const [persRes, pubRes] = await Promise.all([
            apiFetch(`${API}/api/schedules?year=${y}&month=${parseInt(m)}`, { headers: authHeaders() }),
            apiFetch(`${API}/api/schedules/public?year=${y}&month=${parseInt(m)}`, { headers: authHeaders() }),
        ]);
        const personal = persRes ? (await persRes.json()).filter(s => s.date === _scheduleDate) : [];
        const publicSched = pubRes
            ? (await pubRes.json()).filter(s => s.date === _scheduleDate && !s.cancelled)
            : [];

        // 标记未读公开日程为已读（等待全部完成再刷新，避免时序问题）
        const unreadIds = publicSched.filter(ps => !ps.is_read).map(ps => ps.id);
        if (unreadIds.length) {
            await Promise.all(unreadIds.map(id =>
                apiFetch(`${API}/api/schedules/public/${id}/read`, {
                    method: 'POST', headers: authHeaders(),
                }).catch(() => {})
            ));
            refreshCalendar();
        }

        renderDaySchedules(personal, publicSched);
    } catch {
        content.innerHTML = '<p class="text-center text-red-500 text-sm py-8">加载失败</p>';
    }
}

function renderDaySchedules(personal, publicSched) {
    const content = document.getElementById('schedule-day-content');
    if (!personal.length && !publicSched.length) {
        content.innerHTML = '<p class="text-center text-gray-400 text-sm py-8">当前日期你没有日程</p>';
        return;
    }

    const todayStr = new Date().toISOString().slice(0, 10);
    const isPast = _scheduleDate < todayStr;
    const cards = [];

    // 公开日程优先展示
    for (const s of publicSched) {
        const who = s.teacher_nickname || s.teacher_username;
        const canCancel = !isPast && typeof user !== 'undefined' && user.role === 'teacher';
        cards.push(`
            <div class="min-w-[200px] max-w-[240px] bg-red-50 border border-red-100 rounded-xl p-4 flex-shrink-0 flex flex-col">
                <div class="text-[10px] text-red-400 mb-1.5">${s.course_name} · ${who}</div>
                <div class="font-medium text-gray-800 text-sm mb-1">${s.title}</div>
                ${s.content ? `<div class="text-xs text-gray-500 whitespace-pre-wrap flex-1">${s.content}</div>` : '<div class="flex-1"></div>'}
                ${canCancel ? `<button onclick="cancelPublicSchedule(${s.id})" class="mt-3 text-xs text-red-500 hover:text-red-700 self-start">取消日程</button>` : ''}
            </div>`);
    }

    // 个人日程
    for (const s of personal) {
        const safeTitle = s.title.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const safeContent = (s.content || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        cards.push(`
            <div class="min-w-[200px] max-w-[240px] bg-blue-50 border border-blue-100 rounded-xl p-4 flex-shrink-0 flex flex-col">
                <div class="font-medium text-gray-800 text-sm mb-1">${s.title}</div>
                ${s.content ? `<div class="text-xs text-gray-500 whitespace-pre-wrap flex-1">${s.content}</div>` : '<div class="flex-1"></div>'}
                ${isPast ? '' : `<div class="flex justify-end gap-3 mt-3">
                    <button onclick="openEditScheduleForm(${s.id},'${safeTitle}','${safeContent}')" class="text-xs text-blue-500 hover:text-blue-700">编辑</button>
                    <button onclick="deletePersonalSchedule(${s.id})" class="text-xs text-red-500 hover:text-red-700">删除</button>
                </div>`}
            </div>`);
    }

    const wrap = cards.length > 1
        ? `<div class="flex gap-3 overflow-x-auto pb-1">${cards.join('')}</div>`
        : cards[0];
    content.innerHTML = wrap;
}

// ── 日程表单 ─────────────────────────────────────────────────────────────────

function openAddScheduleForm() {
    _editingScheduleId = null;
    _schedOrigTitle = '';
    _schedOrigContent = '';
    document.getElementById('schedule-form-title').textContent = '添加日程';
    document.getElementById('sched-title-input').value = '';
    document.getElementById('sched-content-input').value = '';
    const pubSec = document.getElementById('sched-public-section');
    if (pubSec) {
        pubSec.classList.toggle('hidden', !(typeof user !== 'undefined' && user.role === 'teacher'));
        const chk = document.getElementById('sched-public-check');
        if (chk) chk.checked = false;
        document.getElementById('sched-course-select-wrapper')?.classList.add('hidden');
    }
    document.getElementById('modal-schedule-form').classList.remove('hidden');
}

function openEditScheduleForm(id, title, content) {
    _editingScheduleId = id;
    _schedOrigTitle = title;
    _schedOrigContent = content;
    document.getElementById('schedule-form-title').textContent = '编辑日程';
    document.getElementById('sched-title-input').value = title;
    document.getElementById('sched-content-input').value = content;
    document.getElementById('sched-public-section')?.classList.add('hidden');
    document.getElementById('modal-schedule-form').classList.remove('hidden');
}

function closeScheduleForm() {
    const title = document.getElementById('sched-title-input').value.trim();
    const content = document.getElementById('sched-content-input').value.trim();
    const hasChanges = _editingScheduleId !== null
        ? (title !== _schedOrigTitle || content !== _schedOrigContent)
        : (title || content);
    if (hasChanges && !confirm('当前已有内容正在编辑，是否退出？')) return;
    document.getElementById('sched-title-input').value = '';
    document.getElementById('sched-content-input').value = '';
    document.getElementById('modal-schedule-form').classList.add('hidden');
}

function togglePublicScheduleOptions() {
    const checked = document.getElementById('sched-public-check').checked;
    document.getElementById('sched-course-select-wrapper').classList.toggle('hidden', !checked);
    if (checked) populateSchedCourseSelect();
}

async function populateSchedCourseSelect() {
    const sel = document.getElementById('sched-course-select');
    if (!sel) return;
    let courses = [];
    if (typeof _teacherCourses !== 'undefined' && _teacherCourses.length) {
        courses = _teacherCourses;
    } else {
        const res = await apiFetch(`${API}/api/courses/`, { headers: authHeaders() });
        if (res) courses = await res.json();
    }
    sel.innerHTML = '<option value="">-- 选择关联课程 --</option>' +
        courses.map(c => `<option value="${c.course_key}">${c.name}</option>`).join('');
}

async function saveSchedule() {
    const title = document.getElementById('sched-title-input').value.trim();
    const content = document.getElementById('sched-content-input').value.trim();
    if (!title) { alert('请填写日程标题'); return; }

    const isPublic = document.getElementById('sched-public-check')?.checked;

    let res;
    if (isPublic) {
        const courseKey = document.getElementById('sched-course-select').value;
        if (!courseKey) { alert('请选择关联课程'); return; }
        res = await apiFetch(`${API}/api/schedules/public`, {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ date: _scheduleDate, title, content, course_key: courseKey }),
        });
    } else if (_editingScheduleId !== null) {
        res = await apiFetch(`${API}/api/schedules/${_editingScheduleId}`, {
            method: 'PUT', headers: authHeaders(),
            body: JSON.stringify({ title, content }),
        });
    } else {
        res = await apiFetch(`${API}/api/schedules`, {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ date: _scheduleDate, title, content }),
        });
    }

    if (!res || !res.ok) { alert('操作失败，请重试'); return; }

    document.getElementById('sched-title-input').value = '';
    document.getElementById('sched-content-input').value = '';
    document.getElementById('modal-schedule-form').classList.add('hidden');
    await loadDaySchedules();
    refreshCalendar();
}

async function deletePersonalSchedule(id) {
    if (!confirm('确认删除此日程？')) return;
    const res = await apiFetch(`${API}/api/schedules/${id}`, { method: 'DELETE', headers: authHeaders() });
    if (!res || !res.ok) { alert('删除失败'); return; }
    await loadDaySchedules();
    refreshCalendar();
}

async function cancelPublicSchedule(id) {
    if (!confirm('确认取消此公开日程？\n\n选课学生将收到取消通知。')) return;
    const res = await apiFetch(`${API}/api/schedules/public/${id}`, { method: 'DELETE', headers: authHeaders() });
    if (!res || !res.ok) { alert('操作失败'); return; }
    await loadDaySchedules();
    refreshCalendar();
}

// ── 日程通知（Step 14-15） ────────────────────────────────────────────────────

async function checkScheduleNotifications() {
    try {
        const res = await apiFetch(`${API}/api/schedules/notifications`, { headers: authHeaders() });
        if (!res || !res.ok) return;
        const notifs = await res.json();
        if (!notifs.length) return;
        for (const n of notifs) {
            await _showScheduleNotification(n);
        }
    } catch { /* silent */ }
}

async function _showScheduleNotification(n) {
    const teacher = n.teacher_nickname || n.teacher_username;
    const [y, m, d] = n.date.split('-').map(Number);
    const dateLabel = `${y}年${m}月${d}日`;
    let msg;
    if (n.type === 'new') {
        msg = `${n.course_name}老师${teacher}发布了《${n.title}》日程，注意在日历查看详情！`;
    } else {
        msg = `${dateLabel}《${n.title}》日程已取消，注意后续消息`;
    }

    await new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black/40 z-[100] flex items-center justify-center';
        overlay.innerHTML = `
            <div class="bg-white rounded-2xl shadow-xl p-6 w-80 max-w-[90vw]">
                <div class="flex items-start gap-3 mb-4">
                    <i class="fas fa-bell text-blue-500 mt-0.5 shrink-0"></i>
                    <p class="text-sm text-gray-700 leading-relaxed">${msg}</p>
                </div>
                <button id="_notif-ok" class="w-full py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">知道了</button>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#_notif-ok').onclick = () => {
            document.body.removeChild(overlay);
            resolve();
        };
    });

    // 标记已展示
    apiFetch(`${API}/api/schedules/notifications/${n.id}/shown`, {
        method: 'POST', headers: authHeaders(),
    }).catch(() => {});
}
