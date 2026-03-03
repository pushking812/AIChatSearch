class ChatController:
    def __init__(self):
        self.chats = []
        self.filtered_chats = []
        self.selected_chats = []
        self.visible_pairs = []
        self.current_pair_index = None

    # ---------- DATA ----------

    def set_chats(self, chats):
        self.chats = chats or []
        self.filtered_chats = list(self.chats)
        self.selected_chats = []
        self.visible_pairs = []
        self.current_pair_index = None

    # ---------- CHAT SELECTION ----------

    def select_chats(self, chats):
        self.selected_chats = chats or []
        self._rebuild_visible_pairs()

    def _rebuild_visible_pairs(self):
        self.visible_pairs = []
        for chat in self.selected_chats:
            for pair in chat.get_pairs():
                self.visible_pairs.append((chat, pair))
        self.current_pair_index = None

    # ---------- NAVIGATION ----------

    def select_pair_by_index(self, index):
        if 0 <= index < len(self.visible_pairs):
            self.current_pair_index = index
            return self.visible_pairs[index][1]
        return None

    def prev_pair(self):
        if self.current_pair_index is None:
            return None
        if self.current_pair_index > 0:
            self.current_pair_index -= 1
            return self.visible_pairs[self.current_pair_index][1]
        return None

    def next_pair(self):
        if self.current_pair_index is None:
            return None
        if self.current_pair_index < len(self.visible_pairs) - 1:
            self.current_pair_index += 1
            return self.visible_pairs[self.current_pair_index][1]
        return None

    # ---------- GETTERS ----------

    def get_visible_pairs(self):
        return self.visible_pairs

    def get_nav_state(self):
        if not self.visible_pairs or self.current_pair_index is None:
            return False, False

        return (
            self.current_pair_index > 0,
            self.current_pair_index < len(self.visible_pairs) - 1,
        )