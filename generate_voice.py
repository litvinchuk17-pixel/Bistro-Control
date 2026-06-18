#!/usr/bin/env python3
"""
Генератор голосу для bvd_v2.mp4
Запусти на своєму Mac: python3 generate_voice.py

Вимоги:
  pip install edge-tts imageio-ffmpeg

Після запуску: voice_track.mp3 з'явиться в папці.
Потім: python3 add_voice.py   ← з'єднає голос з відео.
"""
import asyncio, os, subprocess, sys

# Auto-install edge-tts
try:
    import edge_tts
except ImportError:
    os.system("pip install edge-tts -q")
    import edge_tts

# Auto-install imageio-ffmpeg for bundled ffmpeg binary
try:
    import imageio_ffmpeg
    _FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FF = "ffmpeg"

_HERE = os.path.dirname(os.path.abspath(__file__))

VOICE = "uk-UA-OstapNeural"

SEGMENTS = [
    # HOOK (0:00)
    (1.0,  "Два чоловіки."),
    (1.8,  "Обидва мають десятки мільярдів доларів."),
    (1.5,  "Обидва вважаються найкращими інвесторами в історії людства."),
    (1.2,  "І вони повністю, тотально, категорично не згодні один з одним."),

    # SPLIT VS (9.5)
    (3.0,  "Перший каже: знайди одну чудову компанію і тримай вічно."),
    (1.5,  "Другий каже: не намагайся вгадати переможця. Взагалі. Ніколи."),

    # CTA (21.5)
    (2.0,  "Уяви, що тобі дали десять тисяч доларів прямо зараз."),
    (1.5,  "Якби ВАМ дали десять тисяч — чий підхід ви б обрали?"),
    (1.0,  "Пишіть у коментарях: Баффет або Даліо."),

    # ACT 2 (37.0)
    (2.5,  "Акт другий. Дві релігії."),

    # BUFFETT (43.5)
    (2.0,  "Уоррен Баффет вважає диверсифікацію — визнанням власної слабкості."),
    (2.0,  "Диверсифікація — це захист від невігластва."),
    (1.5,  "Якщо ти знаєш, що робиш — вона тобі не потрібна."),
    (2.0,  "Він читає тисячі звітів, щоб знайти одну компанію."),
    (1.5,  "Coca-Cola. Apple. American Express."),
    (2.0,  "Він не купує ринок. Він купує переконання."),

    # BLOOMBERG BUFFETT (86.5)
    (3.0,  "Berkshire Hathaway. Дев'ятсот мільярдів активів."),

    # BUFFETT PHILOSOPHY (97.5)
    (1.5,  "Купуй великий бізнес. Тримай вічно."),

    # BLOOMBERG DALIO (112.5)
    (3.0,  "Bridgewater Associates. Найбільший хедж-фонд у світі."),

    # DALIO PROFILE (124.5)
    (2.0,  "Рей Даліо дивиться на Баффета і думає одне:"),
    (1.5,  "Ти граєш в рулетку і називаєш це мистецтвом."),
    (2.0,  "Ніхто не може передбачити майбутнє. Навіть я."),
    (2.0,  "Тому він будує систему, яка виграє незалежно від того, хто переможе."),
    (2.0,  "All Weather Portfolio: зростання, рецесія, інфляція, дефляція."),
    (2.0,  "Він не намагається вгадати погоду. Він одягається для будь-якої погоди."),

    # DALIO PHILOSOPHY (168.5)
    (1.5,  "Ніхто не вгадає майбутнє. Навіть найкращий."),

    # BRIDGE (183.5)
    (1.5,  "Це не просто різні стратегії."),
    (1.2,  "Це різні релігії."),

    # NEWSPAPER (191.5)
    (2.0,  "Жовтень 2008. Нью-Йорк Таймс публікує статтю Баффета."),
    (2.0,  "Купуйте американські активи. Я купую."),

    # ACT 3 (202.5)
    (1.5,  "Акт третій. Момент істини."),

    # 2008 CRISIS (209.0)
    (1.5,  "Жовтень 2008. Фінансова система буквально розвалюється на частини."),
    (2.0,  "Баффет купує мільярдами, поки всі продають у паніці."),
    (2.0,  "Bridgewater Даліо показує плюс чотирнадцять відсотків."),
    (2.0,  "Поки індекс S&P 500 впав на мінус тридцять сім відсотків."),

    # BREAKING NEWS (253.0)
    (2.0,  "Найбільша криза з часів Великої депресії."),

    # 2008 SPLIT (263.0)
    (2.0,  "Один переміг завдяки сміливості. Другий — завдяки структурі."),

    # NOT BUFFETT (277.0)
    (2.0,  "Ось у чому проблема, про яку ніхто не каже вголос."),
    (1.5,  "Стратегія Баффета працює — тільки якщо ти Баффет."),
    (2.0,  "Дев'яносто дев'ять відсотків людей, що копіюють його,"),
    (1.5,  "просто грають в азартну гру з додатковими кроками."),

    # ACT 4 (292.5)
    (1.5,  "Акт четвертий. Хто ти насправді?"),

    # PERSONALITY TEST (299.0)
    (2.0,  "Зараз найважливіша частина відео. Забудь про гроші на секунду."),
    (2.0,  "Це питання не про інвестиції. Це питання про те, хто ти є."),
    (2.5,  "Ти Баффет — якщо любиш читати звіти і вивчати бізнес роками."),
    (2.5,  "Ти Даліо — якщо хочеш спати спокійно і не перевіряти новини щодня."),

    # PLOT TWIST (375.5)
    (2.0,  "А тепер дозволь зламати тобі шаблон."),
    (2.0,  "Сам Баффет рекомендує дев'яносто відсотків звичайних людей..."),
    (1.5,  "робити те, що каже Даліо."),
    (2.5,  "Зачекай. Що?"),
    (2.0,  "Найвідоміший прихильник вибору однієї компанії"),
    (2.0,  "сам каже звичайним людям — диверсифікуйте."),
    (2.5,  "Баффет-стратегія — для Баффета, генія аналізу."),
    (2.0,  "Для всіх інших — Даліо."),

    # ACT 5 (460.5)
    (1.5,  "Акт п'ятий. Фінальний вирок."),

    # VERDICT (467.0)
    (2.0,  "Правда, яку ніхто не хоче чути."),
    (1.5,  "Це не битва. Це дзеркало."),
    (2.5,  "Якщо в тебе є час, пристрасть і психологічна стійкість — Баффет."),
    (2.5,  "Якщо хочеш стабільне зростання без нервових зривів — Даліо."),
    (2.0,  "Питання не хто розумніший."),
    (2.0,  "Питання — хто ти, коли ринок падає на сорок відсотків за тиждень."),

    # FINAL CTA (524.0)
    (2.0,  "Тобі дали десять тисяч доларів. Твоя відповідь змінилась?"),
    (2.0,  "Напиши в коментарях: Я Баффет або Я Даліо — і чому."),
    (1.5,  "До зустрічі."),
]


async def generate():
    print(f"Voice: {VOICE}")
    all_parts = []

    for i, (pause, text) in enumerate(SEGMENTS):
        out = os.path.join(_HERE, f"_voice_{i:03d}.mp3")
        if os.path.exists(out):
            print(f"  [{i+1}/{len(SEGMENTS)}] skip (exists): {text[:45]}...")
        else:
            print(f"  [{i+1}/{len(SEGMENTS)}] {text[:45]}...")
            comm = edge_tts.Communicate(text, VOICE, rate="-5%", pitch="-3Hz")
            await comm.save(out)
        all_parts.append((pause, out))

    print("Merging segments with FFmpeg...")
    _merge(all_parts)


def _make_silence(duration_s, out_path):
    """Generate a silent MP3 of given duration using FFmpeg."""
    subprocess.run([
        _FF, "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration_s),
        "-c:a", "libmp3lame", "-b:a", "128k",
        out_path
    ], check=True, capture_output=True)


def _merge(parts):
    tmp_files = []
    concat_entries = []

    # 0.5s lead-in silence
    lead = os.path.join(_HERE, "_sil_lead.mp3")
    _make_silence(0.5, lead)
    tmp_files.append(lead)
    concat_entries.append(lead)

    for i, (pause_s, path) in enumerate(parts):
        if pause_s > 0.01:
            sil = os.path.join(_HERE, f"_sil_{i:03d}.mp3")
            _make_silence(pause_s, sil)
            tmp_files.append(sil)
            concat_entries.append(sil)
        concat_entries.append(path)

    # Write concat list
    concat_txt = os.path.join(_HERE, "_concat.txt")
    with open(concat_txt, "w") as f:
        for entry in concat_entries:
            f.write(f"file '{entry}'\n")
    tmp_files.append(concat_txt)

    out_path = os.path.join(_HERE, "voice_track.mp3")
    result = subprocess.run([
        _FF, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-ar", "44100",
        "-c:a", "libmp3lame", "-b:a", "128k",
        out_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error:\n{result.stderr[-800:]}")
        raise RuntimeError("FFmpeg concat failed")

    # Cleanup temp silences and concat list
    for f in tmp_files:
        if os.path.exists(f):
            os.remove(f)
    # Cleanup voice segment files
    for _, path in parts:
        if os.path.exists(path):
            os.remove(path)

    # Get duration via ffprobe
    probe = subprocess.run(
        [_FF, "-i", out_path],
        capture_output=True, text=True
    )
    dur_line = [l for l in probe.stderr.splitlines() if "Duration" in l]
    duration = dur_line[0].split("Duration:")[1].split(",")[0].strip() if dur_line else "?"
    print(f"✓ voice_track.mp3 ready  (duration: {duration})")
    print(f"  Next: python3 add_voice.py")


asyncio.run(generate())
