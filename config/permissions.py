BASE_SEND_PERMS = {
    "view_channel": "Visualizzare il canale",
    "send_messages": "Inviare messaggi",
    "embed_links": "Inviare embed",
}

READ_HISTORY_PERMS = {
    "read_message_history": "Leggere la cronologia messaggi",
}

MANAGE_CHANNEL_PERMS = {
    "manage_channels": "Gestire i canali",
}

LOBBY_CODES_CHANNEL_PERMS = (
    BASE_SEND_PERMS
    | MANAGE_CHANNEL_PERMS
)

RANKING_CHANNEL_PERMS = (
    BASE_SEND_PERMS
)