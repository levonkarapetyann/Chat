const socket = io();
let currentPartnerId = null;

function getCurrentUserId() {
    const chatRoot = document.getElementById('chat-root');
    return chatRoot ? chatRoot.dataset.currentUserId : null;
}

socket.on('new_message', function(data) {
    const currentUserId = getCurrentUserId();
    if (currentPartnerId && (data.sender_id == currentPartnerId || data.sender_id == currentUserId)) {
        appendMessage(data.text, data.sender_id == currentUserId, 'Just now');
        scrollToBottom();
    }
});

function selectChat(partnerId, fullName, username) {
    currentPartnerId = partnerId;
    const currentUserId = getCurrentUserId();
    
    document.getElementById('chat-window-placeholder').classList.add('hidden');
    document.getElementById('chat-window-active').classList.remove('hidden');
    
    document.getElementById('active-user-name').innerText = fullName;
    document.getElementById('active-user-username').innerText = '@' + username;

    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('bg-white', 'shadow-xs', 'border-gray-100');
    });
    const activeItem = document.getElementById(`chat-user-${partnerId}`);
    if (activeItem) {
        activeItem.classList.add('bg-white', 'shadow-xs', 'border-gray-100');
    }

    socket.emit('join', { partner_id: partnerId });

    fetch(`/get_messages/${partnerId}`)
        .then(response => response.json())
        .then(messages => {
            const container = document.getElementById('messages-container');
            container.innerHTML = '';
            messages.forEach(msg => {
                appendMessage(msg.text, msg.sender_id == currentUserId, msg.timestamp);
            });
            scrollToBottom();
        });
}

function appendMessage(text, isMe, timestamp) {
    const container = document.getElementById('messages-container');
    const msgWrapper = document.createElement('div');
    msgWrapper.className = `flex ${isMe ? 'justify-end' : 'justify-start'}`;

    const msgBubble = document.createElement('div');
    msgBubble.className = `max-w-xs md:max-w-md p-3 rounded-xl shadow-xs text-sm relative ${
        isMe ? 'bg-gray-900 text-white' : 'bg-white text-gray-800 border border-gray-100'
    }`;

    msgBubble.innerHTML = `
        <p class="break-words pr-8">${text}</p>
        <span class="absolute bottom-1 right-2 text-[10px] text-gray-400">${timestamp}</span>
    `;

    msgWrapper.appendChild(msgBubble);
    container.appendChild(msgWrapper);
}

function sendMessage(event) {
    event.preventDefault();
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    
    if (text && currentPartnerId) {
        socket.emit('send_message', {
            recipient_id: currentPartnerId,
            text: text
        });
        input.value = '';
    }
}

document.getElementById('search-btn').addEventListener('click', function() {
    const usernameInput = document.getElementById('search-username');
    let username = usernameInput.value.trim().toLowerCase();
    
    if (username.startsWith('@')) {
        username = username.substring(1);
    }

    const errorEl = document.getElementById('search-error');
    errorEl.classList.add('hidden');

    if (!username) return;

    fetch(`/search_user?username=${username}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                usernameInput.value = '';
                const u = data.user;
                
                if (!document.getElementById(`chat-user-${u.id}`)) {
                    const chatsList = document.getElementById('chats-list');
                    
                    const fLetter = u.first_name ? u.first_name[0] : '?';
                    const lLetter = u.last_name ? u.last_name[0] : '?';
                    const initials = (fLetter + lLetter).toUpperCase();
                    
                    const chatHtml = `
                        <div onclick="selectChat('${u.id}', '${u.first_name} ${u.last_name}', '${u.username}')" 
                             id="chat-user-${u.id}"
                             class="chat-item flex items-center p-2.5 rounded-xl cursor-pointer hover:bg-white hover:shadow-xs border border-transparent transition-all group">
                            <div class="w-8 h-8 bg-gray-100 text-gray-600 rounded-lg flex items-center justify-center font-medium text-xs mr-3 group-hover:bg-gray-900 group-hover:text-white transition-colors">
                                ${initials}
                            </div>
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-normal text-gray-700 truncate group-hover:text-gray-900">${u.first_name} ${u.last_name}</p>
                            </div>
                        </div>
                    `;
                    chatsList.insertAdjacentHTML('beforeend', chatHtml);
                }
                selectChat(u.id, `${u.first_name} ${u.last_name}`, u.username);
            } else {
                errorEl.innerText = data.message;
                errorEl.classList.remove('hidden');
            }
        })
        .catch(err => console.error("Error searching:", err));
});

document.getElementById('search-username').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.getElementById('search-btn').click();
    }
});

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}