Швейцарка без BYE			- Swiss with Dropdowns / Hybrid Swiss-Elimination with Fillers
Швейцарка Классик			- Triple Elimination
Швейцарка Без выбывания		- Swiss Without Elimination
Швейцарка + Плей Офф		- Swiss to Single Elimination / Top Cut

Олимпийка					- Single Elimination
Олимпийка с нижней сеткой	- Double Elimination
Швейцарка + Олимпийка		- Swiss Qualifier / Swiss Group Stage

Круговая					- Round Robin


-- 1. Таблица игроков (глобальный список)
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Таблица турниров
CREATE TABLE tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    system_type TEXT NOT NULL,         -- 'swiss', 'single_elim', 'double_elim', 'round_robin'
    status TEXT DEFAULT 'setup',        -- 'setup', 'active', 'finished'
    
    -- ГИБКИЕ НАСТРОЙКИ
    max_losses_to_elim INTEGER DEFAULT NULL, -- Кол-во поражений до вылета (например, 3 для Triple Elimination, 1 для Single)
    prize_places_count INTEGER DEFAULT 3,    -- Кол-во призовых мест
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (system_type IN ('swiss', 'single_elim', 'double_elim', 'round_robin')),
    CHECK (status IN ('setup', 'active', 'finished'))
);

-- 3. Связующая таблица: Участники конкретного турнира (для сохранения истории)
CREATE TABLE tournament_participants (
    tournament_id INTEGER,
    player_id INTEGER,
    initial_seed INTEGER, -- Начальный рейтинг/посев для жеребьевки
    PRIMARY KEY (tournament_id, player_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

-- 4. Таблица раундов / туров
CREATE TABLE rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL, -- 1, 2, 3...
    bracket_type TEXT DEFAULT 'main', -- 'main' (круговая/швейцарка/олимпийская), 'winners', 'losers' (для double elimination)
    is_completed BOOLEAN DEFAULT 0,
	completed_at TIMESTAMP,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    UNIQUE(tournament_id, round_number, bracket_type)
);

-- 5. Таблица матчей
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id INTEGER NOT NULL,
    player1_id INTEGER, -- Может быть NULL, если соперник еще не определен (в сетках)
    player2_id INTEGER, -- Может быть NULL (или специальный ID 'BYE' для автоматического прохода)
    
    -- Поля для олимпийских сеток и Double Elimination: откуда приходят игроки
    p1_from_match_id INTEGER, 
    p2_from_match_id INTEGER,
    
    status TEXT DEFAULT 'scheduled', -- 'scheduled', 'live', 'completed', 'bye'
    winner_id INTEGER,
    
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE,
    FOREIGN KEY (player1_id) REFERENCES players(id),
    FOREIGN KEY (player2_id) REFERENCES players(id),
    FOREIGN KEY (winner_id) REFERENCES players(id),
    CHECK (status IN ('scheduled', 'live', 'completed', 'bye'))
);

-- 6. Детализация счета (партия / сет / индивидуальные очки)
CREATE TABLE match_results (
    match_id INTEGER PRIMARY KEY,
    player1_score INTEGER DEFAULT 0,
    player2_score INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
);

-- 2. Новая таблица: Текущие метрики и коэффициенты участников в турнире
-- Данные пересчитываются на Python после каждого раунда
CREATE TABLE tournament_standings (
    tournament_id INTEGER,
    player_id INTEGER,
    
    points REAL DEFAULT 0.0,             -- Основные очки (например, 1 за победу, 0.5 за ничью)
    matches_played INTEGER DEFAULT 0,    -- Всего сыграно матчей
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    is_eliminated BOOLEAN DEFAULT 0,     -- Выбыл ли игрок по лимиту поражений (для Triple/Swiss)
    
    -- ДОПОЛНИТЕЛЬНЫЕ РЕЙТИНГИ (Критерии тай-брейка)
    buchholz_score REAL DEFAULT 0.0,     -- Коэффициент Бухгольца (сумма очков всех соперников)
    median_buchholz REAL DEFAULT 0.0,    -- Срединный Бухгольц (без лучшего и худшего результата)
    sonneborn_berger REAL DEFAULT 0.0,   -- Коэффициент Зоннеборна-Бергера (для круговой)
    progress_score REAL DEFAULT 0.0,     -- Коэффициент прогресса (сумма нарастающих очков по турам)
    
    current_rank INTEGER,                -- Текущее место в таблице турнира
    
    PRIMARY KEY (tournament_id, player_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

