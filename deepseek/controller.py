class ChatController:
    def __init__(self):
        self.chats = []
        self.filtered_chats = []

        self.current_chat = None
        self.current_chat_pairs = []
        self.current_index_in_chat = None

    # ---------- DATA ----------

    def set_chats(self, chats):
        self.chats = chats or []
        self.filtered_chats = list(self.chats)
        self.current_chat = None
        self.current_chat_pairs = []
        self.current_index_in_chat = None

    def get_filtered_chats(self):
        return self.filtered_chats

    # ---------- FILTER ----------

    def filter_chats(self, query):
        query = (query or "").lower().strip()

        if not query:
            self.filtered_chats = list(self.chats)
        else:
            self.filtered_chats = [
                chat for chat in self.chats
                if query in chat.title.lower()
            ]

        self.current_chat = None
        self.current_chat_pairs = []
        self.current_index_in_chat = None

    # ---------- SELECT MESSAGE ----------

    def select_pair(self, chat, pair):
        pairs = chat.get_pairs()
        for i, p in enumerate(pairs):
            if p is pair:
                self.current_chat = chat
                self.current_chat_pairs = pairs
                self.current_index_in_chat = i
                return p
        return None

    # ---------- NAVIGATION ----------

    def prev_pair(self):
        if self.current_index_in_chat is None:
            return None

        if self.current_index_in_chat > 0:
            self.current_index_in_chat -= 1
            return self.current_chat_pairs[self.current_index_in_chat]

        return None

    def next_pair(self):
        if self.current_index_in_chat is None:
            return None

        if self.current_index_in_chat < len(self.current_chat_pairs) - 1:
            self.current_index_in_chat += 1
            return self.current_chat_pairs[self.current_index_in_chat]

        return None

    def get_nav_state(self):
        if self.current_index_in_chat is None:
            return False, False

        return (
            self.current_index_in_chat > 0,
            self.current_index_in_chat < len(self.current_chat_pairs) - 1,
        )

    def get_position_info(self):
        if self.current_chat is None or self.current_index_in_chat is None:
            return None, None, None

        return (
            self.current_chat.title,
            self.current_index_in_chat + 1,
            len(self.current_chat_pairs),
        )
