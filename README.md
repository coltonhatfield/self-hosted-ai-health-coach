# Self-Hosted AI Health & Fitness Dashboard

I built this project to solve a personal problem: trying to balance competitive club volleyball training while keeping my infrastructure and homelab skills sharp. I was tired of using disjointed, subscription-based apps to track my macros, sleep, and workouts, so I decided to spin up an Ubuntu VM and self-host the whole pipeline.

This is a full-stack dashboard that pulls my Apple Health data, estimates macros from food pictures, and uses an LLM to generate daily lifting plans based on my actual soreness and energy levels.

## What's under the hood?
* **Infrastructure:** Running via Docker Compose on a Proxmox VM, accessed securely remotely over Tailscale.
* **Backend:** FastAPI (Python) handles the routing, scheduling, and webhook ingestion.
* **Databases:** * **InfluxDB:** Handles the heavy lifting for time-series data (Apple Health stats, macro totals).
  * **SQLite:** Stores relational text data (daily journal, AI advice, saved workouts).
* **Frontend:** A lightweight, mobile-friendly HTML/JS web app to log data on the go.
* **Visualization:** Grafana for all the charts, widgets, and trend analysis.
* **AI Integration:** Google Gemini 2.5 Flash for vision parsing (food macros) and text generation (daily coaching and workout plans).

## Core Features
* **Apple Health Automation:** An iOS Shortcut automatically pushes my daily steps, resting energy, and sleep data to the API every night.
* **Frictionless Food Logging:** I can snap a picture of my meal or type a quick description, and the AI vision model parses the estimated protein, carbs, and fats directly into the database.
* **Dynamic Workout Generator:** I input my daily soreness and energy levels, and the AI generates a customized workout plan specifically tuned for athletic explosiveness. It adapts on the fly if I tell it I have a tweaked wrist or just played a 3-hour tournament.
* **Daily Journal:** A persistent feedback loop where I can log my training hours and notes so the AI "remembers" my recent physical load.

## To Run It Yourself
1. Clone this repo.
2. Rename `.env.example` to `.env` and drop in your API keys.
3. Run `docker-compose up -d`.
4. Setup Shortcuts on iphone to send data from health app to server
5. Point your Grafana data source to the Influx container and start building panels.
