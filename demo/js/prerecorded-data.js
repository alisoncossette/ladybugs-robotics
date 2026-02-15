/* Pre-recorded orchestration session data
   Mirrors the actual BookReaderOrchestrator state machine flow
   against test_data/ images. */

const WALKTHROUGH_SESSION = {
    book: {
        title: "How to Do Just About Anything on a Computer",
        author: "Reader's Digest",
        totalSpreads: 4
    },

    steps: [
        // ═══ CYCLE 1: Book is closed → open it ═══
        {
            id: "cycle-1",
            label: "Cycle 1: Detect & Open",
            image: "images/spread-closed.jpg",
            substeps: [
                {
                    action: "assess_scene",
                    icon: "\uD83D\uDC41",
                    label: "Assess Scene",
                    input: "Camera frame → Google Gemini Vision",
                    result: "book_closed",
                    decision: "Book is present but closed. Execute motor skill.",
                    nextAction: "open_book",
                    elapsed_ms: 1850
                },
                {
                    action: "motor_open_book",
                    icon: "\uD83E\uDDBE",
                    label: "Motor: Open Book",
                    input: "ACT policy: ladybugs/open_book_ACT (15s)",
                    result: "success",
                    decision: "Book cover lifted. Re-assessing scene.",
                    nextAction: "assess_scene",
                    elapsed_ms: 15000,
                    animationOverlay: "images/open-book.gif",
                    motorLabel: "Executing open_book policy..."
                }
            ]
        },

        // ═══ CYCLE 2: Book open → TOC spread → read ═══
        {
            id: "cycle-2",
            label: "Cycle 2: Read TOC Spread",
            image: "images/spread-toc.jpg",
            substeps: [
                {
                    action: "assess_scene",
                    icon: "\uD83D\uDC41",
                    label: "Assess Scene",
                    input: "Camera frame → Google Gemini Vision",
                    result: "book_open",
                    decision: "Book is open, pages visible. Classify page type.",
                    nextAction: "classify_page",
                    elapsed_ms: 1650
                },
                {
                    action: "classify_page",
                    icon: "\uD83C\uDFF7",
                    label: "Classify Page",
                    input: "Spread image → page type classifier",
                    result: "toc",
                    decision: "Table of contents \u2014 readable page. Proceed to read.",
                    nextAction: "read_left",
                    elapsed_ms: 1200
                },
                {
                    action: "read_left",
                    icon: "\uD83D\uDCD6",
                    label: "Read Left Page",
                    input: "Left half of spread \u2192 text extraction + TTS",
                    result: "Contents\n\nHow to use this book ........... 8\nYOU AND YOUR COMPUTER\nGetting Started .................. 14\nKnowing Your Computer ........... 16\nSetting Up Programs ............. 24",
                    decision: "Extracted 32 words. Streaming to ElevenLabs.",
                    elapsed_ms: 3200,
                    audio: "audio/toc-reading.mp3",
                    audioEnd: 12
                },
                {
                    action: "read_right",
                    icon: "\uD83D\uDCD6",
                    label: "Read Right Page",
                    input: "Right half of spread \u2192 text extraction + TTS",
                    result: "PRACTICAL HOME PROJECTS\nMake address labels ............ 172\nPicture Perfect ................ 186\nCreate a greeting card ......... 198",
                    decision: "Extracted 24 words. Streaming to ElevenLabs.",
                    elapsed_ms: 2800,
                    audio: "audio/toc-reading.mp3",
                    audioStart: 12
                },
                {
                    action: "turn_page",
                    icon: "\uD83E\uDDBE",
                    label: "Motor: Turn Page",
                    input: "ACT policy: ladybugs/turn_page_ACT (10s)",
                    result: "success \u2714 hash changed",
                    decision: "Page turned. Frame hash changed \u2192 verified. Continue.",
                    nextAction: "assess_scene",
                    elapsed_ms: 10000,
                    animationOverlay: "images/page-turn.gif",
                    motorLabel: "Executing turn_page policy..."
                }
            ]
        },

        // ═══ CYCLE 3: Content page → read ═══
        {
            id: "cycle-3",
            label: "Cycle 3: Read Content",
            image: "images/spread-content.jpg",
            substeps: [
                {
                    action: "assess_scene",
                    icon: "\uD83D\uDC41",
                    label: "Assess Scene",
                    input: "Camera frame → Google Gemini Vision",
                    result: "book_open",
                    decision: "Book is open, pages visible. Classify page type.",
                    nextAction: "classify_page",
                    elapsed_ms: 1700
                },
                {
                    action: "classify_page",
                    icon: "\uD83C\uDFF7",
                    label: "Classify Page",
                    input: "Spread image → page type classifier",
                    result: "content",
                    decision: "Content page \u2014 robot reads this.",
                    nextAction: "read_left",
                    elapsed_ms: 1100
                },
                {
                    action: "read_left",
                    icon: "\uD83D\uDCD6",
                    label: "Read Left Page",
                    input: "Left half of spread \u2192 text extraction + TTS",
                    result: "Hardware Hiccups\n\nMy keyboard isn\u2019t working\n\nHardware or software may be at fault if your keyboard is acting up. First, check that the cable is firmly plugged in. If you use a wireless keyboard, check the batteries. If the problem persists, try restarting your computer.",
                    decision: "Extracted 47 words. Streaming to ElevenLabs (Chantal).",
                    elapsed_ms: 4500,
                    audio: "audio/content-reading.mp3",
                    audioEnd: 18
                },
                {
                    action: "read_right",
                    icon: "\uD83D\uDCD6",
                    label: "Read Right Page",
                    input: "Right half of spread \u2192 text extraction + TTS",
                    result: "Solving Problems\n\nIf the whole keyboard fails, you can try the on-screen keyboard. Go to Start, then Programs, then Accessories, then Accessibility, and select On-Screen Keyboard.",
                    decision: "Extracted 31 words. Streaming to ElevenLabs (Kwame).",
                    elapsed_ms: 3800,
                    audio: "audio/content-reading.mp3",
                    audioStart: 18
                },
                {
                    action: "turn_page",
                    icon: "\uD83E\uDDBE",
                    label: "Motor: Turn Page",
                    input: "ACT policy: ladybugs/turn_page_ACT (10s)",
                    result: "success \u2714 hash changed",
                    decision: "Page turned. Frame hash verified. Continue loop.",
                    nextAction: "assess_scene",
                    elapsed_ms: 10000,
                    animationOverlay: "images/page-turn.gif",
                    motorLabel: "Executing turn_page policy..."
                }
            ]
        },

        // ═══ CYCLE 4: Index → skip → done → close ═══
        {
            id: "cycle-4",
            label: "Cycle 4: Skip & Close",
            image: "images/spread-index.jpg",
            substeps: [
                {
                    action: "assess_scene",
                    icon: "\uD83D\uDC41",
                    label: "Assess Scene",
                    input: "Camera frame → Google Gemini Vision",
                    result: "book_open",
                    decision: "Book is open, pages visible. Classify page type.",
                    nextAction: "classify_page",
                    elapsed_ms: 1600
                },
                {
                    action: "classify_page",
                    icon: "\uD83C\uDFF7",
                    label: "Classify Page",
                    input: "Spread image → page type classifier",
                    result: "index",
                    decision: "Index page \u2014 robot SKIPS this.",
                    nextAction: "turn_page",
                    elapsed_ms: 1100,
                    skipped: true
                },
                {
                    action: "turn_page",
                    icon: "\uD83E\uDDBE",
                    label: "Motor: Turn Page",
                    input: "Skip reading, turn to next spread",
                    result: "success",
                    decision: "Index skipped. Turning to check next spread.",
                    nextAction: "assess_scene",
                    elapsed_ms: 10000,
                    animationOverlay: "images/page-turn.gif",
                    motorLabel: "Executing turn_page policy..."
                },
                {
                    action: "assess_scene",
                    icon: "\uD83D\uDC41",
                    label: "Assess Scene",
                    input: "Camera frame after turn → Google Gemini Vision",
                    result: "book_done",
                    decision: "Last page / back cover reached. Close book.",
                    nextAction: "close_book",
                    elapsed_ms: 1500
                },
                {
                    action: "motor_close_book",
                    icon: "\uD83E\uDDBE",
                    label: "Motor: Close Book",
                    input: "ACT policy: ladybugs/close_book_ACT (15s)",
                    result: "success",
                    decision: "Book closed. Session complete.",
                    elapsed_ms: 15000,
                    animationOverlay: "images/open-book.gif",
                    motorLabel: "Executing close_book policy..."
                }
            ]
        }
    ]
};
