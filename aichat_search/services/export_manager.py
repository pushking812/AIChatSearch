# aichat_search/services/export_manager.py

import os
import logging
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import List, Tuple

from ..model import Chat, MessagePair
from ..gui_components import constants
from .exporter_factory import ExporterFactory
from .exporters.base import Exporter
from .exporters.block_exporter import BlockExporter

logger = logging.getLogger(__name__)


class ExportManager:
    """Управляет экспортом сообщений в различные форматы."""

    def __init__(self, controller, parent_window):
        self.controller = controller
        self.parent = parent_window

    def export_messages(self, selected_pairs: List[Tuple[Chat, MessagePair]], format_type: str = 'txt'):
        if not selected_pairs:
            messagebox.showwarning("Экспорт", "Нет выбранных сообщений для экспорта.", parent=self.parent)
            return

        if format_type == 'txt':
            self._export_txt(selected_pairs)
        elif format_type == 'blocks':
            self._export_blocks(selected_pairs)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    # ------------------------------------------------------------------
    # Экспорт в простой текст
    # ------------------------------------------------------------------

    def _generate_filename(self, source_name: str, chat_title: str, message_index: int) -> str:
        safe_chat_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return constants.EXPORT_FILENAME_TEMPLATE.format(
            source_name=source_name,
            chat_title=safe_chat_title,
            message_index=message_index
        )

    def _export_txt(self, selected_pairs: List[Tuple[Chat, MessagePair]]):
        exporter = ExporterFactory.get_exporter('txt')
        exported_count = 0

        if len(selected_pairs) == 1:
            chat, pair = selected_pairs[0]
            try:
                message_index = chat.pairs.index(pair) + 1
            except ValueError:
                message_index = 0

            data = Exporter.prepare_data(
                chat_title=chat.title,
                chat_created_at=chat.created_at,
                pair=pair,
                message_index=message_index
            )

            source_name_full, _ = self.controller.get_source_info(chat)
            source_name_base = os.path.splitext(source_name_full)[0] if source_name_full != "Imported" else "Imported"
            filename = self._generate_filename(source_name_base, chat.title, message_index)

            file_path = filedialog.asksaveasfilename(
                parent=self.parent,
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=filename,
                title=f"Сохранить сообщение {message_index} из чата '{chat.title}'"
            )
            if not file_path:
                return

            try:
                exporter.export(data, file_path)
                exported_count = 1
            except Exception as e:
                messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл:\n{e}", parent=self.parent)
                return

        else:
            root_dir = filedialog.askdirectory(parent=self.parent, title="Выберите папку для сохранения сообщений")
            if not root_dir:
                return

            for idx, (chat, pair) in enumerate(selected_pairs):
                try:
                    message_index = chat.pairs.index(pair) + 1
                except ValueError:
                    message_index = 0

                data = Exporter.prepare_data(
                    chat_title=chat.title,
                    chat_created_at=chat.created_at,
                    pair=pair,
                    message_index=message_index
                )

                source_name_full, _ = self.controller.get_source_info(chat)
                source_name_base = os.path.splitext(source_name_full)[0] if source_name_full != "Imported" else "Imported"
                filename = self._generate_filename(source_name_base, chat.title, message_index)
                file_path = os.path.join(root_dir, filename)

                try:
                    exporter.export(data, file_path)
                    exported_count += 1
                except Exception as e:
                    messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл:\n{e}", parent=self.parent)
                    answer = messagebox.askyesno(
                        "Ошибка",
                        f"Продолжить экспорт остальных сообщений? (Обработано {exported_count} из {len(selected_pairs)})",
                        parent=self.parent
                    )
                    if not answer:
                        break

        if exported_count:
            if len(selected_pairs) == 1:
                messagebox.showinfo("Экспорт", "Сообщение успешно экспортировано.", parent=self.parent)
            else:
                messagebox.showinfo("Экспорт", f"Успешно экспортировано {exported_count} из {len(selected_pairs)} сообщений в папку:\n{root_dir}", parent=self.parent)
        else:
            messagebox.showinfo("Экспорт", "Ни одно сообщение не было экспортировано.", parent=self.parent)

    # ------------------------------------------------------------------
    # Экспорт по блокам
    # ------------------------------------------------------------------

    def _export_blocks(self, selected_pairs: List[Tuple[Chat, MessagePair]]):
        root_dir = filedialog.askdirectory(parent=self.parent, title="Выберите папку для сохранения блоков")
        if not root_dir:
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        default_folder_name = f"messages-block-export-{timestamp}"
        folder_path = os.path.join(root_dir, default_folder_name)

        all_blocks = []
        block_index = 0
        metadata_lines = []
        total_unclosed = 0

        # Список для сбора информации о незакрытых блоках (для логирования после назначения индексов)
        unclosed_info = []

        for idx, (chat, pair) in enumerate(selected_pairs):
            try:
                message_index_in_chat = chat.pairs.index(pair) + 1
            except ValueError:
                message_index_in_chat = 0

            source_name_full, _ = self.controller.get_source_info(chat)

            data = BlockExporter.prepare_data(
                chat_title=chat.title,
                chat_created_at=chat.created_at,
                pair=pair,
                message_index=message_index_in_chat,
                source_name=source_name_full
            )
            blocks = data.get('blocks', [])
            if not blocks:
                continue

            unclosed = data.get('unclosed_blocks', 0)
            total_unclosed += unclosed

            # Запоминаем незакрытые блоки (они в конце списка)
            if unclosed > 0:
                for i in range(unclosed):
                    local_idx = len(blocks) - unclosed + i
                    unclosed_info.append({
                        'chat_title': chat.title,
                        'source_name': source_name_full,
                        'message_index': message_index_in_chat,
                        'block': blocks[local_idx]
                    })

            # Назначаем глобальные индексы
            for block in blocks:
                block.index = block_index
                block_index += 1

            source_name_base = os.path.splitext(source_name_full)[0] if source_name_full != "Imported" else "Imported"
            metadata_lines.append(f"Сообщение {idx+1}:")
            metadata_lines.append(f"  Чат: {chat.title}")
            metadata_lines.append(f"  Источник: {source_name_base}")
            metadata_lines.append(f"  Номер в чате: {message_index_in_chat}")
            metadata_lines.append(f"  Блоки: {blocks[0].filename()} – {blocks[-1].filename()}")
            if unclosed:
                metadata_lines.append(f"  (незакрытых блоков: {unclosed})")
            metadata_lines.append("")

            all_blocks.extend(blocks)

        # Выводим предупреждения для незакрытых блоков (теперь с глобальными индексами)
        for info in unclosed_info:
            block = info['block']
            logger.warning(
                f'[WARNING] Ошибка парсинга, незакрытый блок: #{block.index} '
                f'(файл: "{info["source_name"]}", чат: "{info["chat_title"]}", '
                f'сообщение #{info["message_index"]})'
            )
            # Отладочная информация о содержимом (можно оставить как debug)
            logger.debug(f"  Содержимое блока (последние 200 символов): {block.content[-200:]}")

        if not all_blocks:
            messagebox.showwarning("Экспорт", "Нет блоков для экспорта.", parent=self.parent)
            return

        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку:\n{e}", parent=self.parent)
            return

        for block in all_blocks:
            file_path = os.path.join(folder_path, block.filename())
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(block.content)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось записать файл {block.filename()}:\n{e}", parent=self.parent)
                if not messagebox.askyesno("Ошибка", "Продолжить экспорт остальных блоков?", parent=self.parent):
                    break

        meta_path = os.path.join(folder_path, "metadata.txt")
        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(f"Экспорт блоков от {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n")
                f.write(f"Всего сообщений: {len(selected_pairs)}\n")
                f.write(f"Всего блоков: {len(all_blocks)}\n")
                if total_unclosed:
                    f.write(f"Незакрытых блоков: {total_unclosed}\n")
                f.write("\n" + "="*60 + "\n\n")
                f.write("\n".join(metadata_lines))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось записать метаданные:\n{e}", parent=self.parent)

        msg = f"Успешно экспортировано {len(all_blocks)} блоков в папку:\n{folder_path}"
        if total_unclosed:
            msg += f"\n\nОбнаружено незакрытых блоков: {total_unclosed}"
        messagebox.showinfo("Экспорт", msg, parent=self.parent)