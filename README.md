# 🏆 CoD Tournament Manager Bot

A Discord bot designed to manage competitive tournaments with automated team management, lobby creation, scoring, and final rankings with generated visual leaderboards.

## 🛠 Tech Stack

- Python 3.12+
- discord.py (app_commands + UI components)
- SQLite / relational database
- Async architecture (async/await)

## 🧠 Architecture

The bot is built around an event-driven architecture:

- Events represent tournament sessions
- Teams belong to events
- Lobbies are dynamically generated per event
- Match results are aggregated into computed rankings

Core logic is separated into:

- services/ → business logic (events, teams, ranking)
- ui/ → Discord views, selects, embeds
- db/ → database abstraction layer

## 📌 Overview

This bot handles the full lifecycle of a tournament:

- Event creation and configuration
- Team registration and management
- Automatic lobby generation
- Match result tracking
- Ranking computation (global and per-lobby)
- Final leaderboard generation with images

Everything is driven by event states and role-based permissions.

## 🔄 Event Lifecycle

Each event follows a strict state flow:

SETUP → READY → RUNNING → FINISHED

Commands are only valid depending on the current event state.

## ⚙️ Core Features

### 🧾 Event Management

- Create and delete events
- View event information
- Automatic event state transitions

### 👥 Team System

- Register teams
- Edit team data
- Remove teams
- View team statistics

### 🏟️ Lobby System

- Automatic lobby generation based on team count
- Multiple balancing modes
- Manual team movement between lobbies
- Lobby inspection tools

### 🎮 Match Handling

- Insert match results
- Validate and edit results
- Accept/reject results
- Penalize teams

### 📊 Rankings

- Global and per-lobby rankings
- Kill-based scoring system
- Placement point system
- Optional penalty system
- Optional worst-match drop system

### 🏁 Tournament Finalization

- Final leaderboard generation
- MVP ranking calculation
- Image-based results export
- Automatic cleanup after completion

## 🎯 Event Modes

### 🎲 Random

- Fully random team distribution
- Flexible number of lobbies

### 🎲 Random (Max 16 teams per lobby)

- Random distribution
- Hard cap of 16 teams per lobby

### ⚔️ KD-Based (Max 16 teams per lobby)

- Teams sorted by K/D ratio
- Distributed into balanced lobbies

### ⚖️ Balanced KD Mode

- Teams sorted by K/D ratio
- Even distribution across a configurable number of lobbies

## 🧮 Scoring System

Team score is calculated using:

- Kill points (configurable multiplier)
- Placement points (per position table)
- Optional penalty points
- Optional worst-match drop rule

Final score is the sum of all match scores per team.

## 🧩 Key Commands

### Setup

- *setup_server*
- *elimina_config_server*

### Events

- *crea_evento*
- *config_lobby*
- *avvia_evento*
- *termina_evento*
- *elimina_evento*

### Teams

- *registra_team*
- *modifica_team*
- *elimina_team*
- *info_team*

### Lobby Control

- *sposta_team*
- *info_lobby*

### Results

- *inserisci_risultato*
- *controlla_risultati*
- *accept_all_results*
- *penalizza_team*

## 📊 Ranking System

Supports:

- Global ranking
- Lobby-based ranking
- MVP ranking (kills-based)
- Custom placement scoring
- Penalty adjustments

## 🖼️ Output

At the end of an event, the bot generates:

- Team leaderboard image
- MVP leaderboard image
- Lobby-specific rankings
- Final embedded summary

## 🔐 Permissions System

- Admin-only commands for tournament control
- Role-based access for event management
- Server-level configuration for global settings

## ⚡ Notes

- Designed for structured competitive tournaments
- Optimized for Call of Duty-style formats
- Fully event-driven architecture
- Supports multi-lobby tournament scaling

## ⚙️ Design Notes

- Fully asynchronous (async/await)
- Built with Discord slash commands (app_commands)
- Uses UI components (Selects, Views, Modals)
- Stateless command execution with database persistence