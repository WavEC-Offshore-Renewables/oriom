import time
from tqdm import tqdm
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeRemainingColumn


def charge_2(duration, steps = 100, phrase = None):
    start = time.time()
    with tqdm(total=duration, bar_format="{l_bar}{bar:40}{r_bar}", desc=phrase) as pbar:
        while True:
            elapsed = time.time() - start
            if elapsed >= duration:
                break
            pbar.update(elapsed - pbar.n)
            time.sleep(0.05)


def charge_1(duration, steps = 100, phrase = None):
    for _ in tqdm(range(steps), desc=phrase, ncols=100):
        time.sleep(duration / steps)



def charge_3(duration,steps = 100, phrase = None):

    with Progress() as progress:
        task = progress.add_task(phrase, total=duration)

        start = time.time()
        while not progress.finished:
            elapsed = time.time() - start
            progress.update(task, completed=elapsed)
            time.sleep(0.05)


def charge_4(duration, steps = 100, phrase = None, bar_width = None, time_show = True):
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
    ) as progress:
        phrase = phrase.ljust(40)
        task = progress.add_task(phrase, total=steps)

        for _ in range(steps):
            time.sleep(0.05)
            progress.update(task, advance=1)

def charge_5(duration, steps = 100, phrase = None, bar_width = None, time_show = True):
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TimeRemainingColumn(),
    ) as progress:
        phrase = phrase.ljust(40)
        task = progress.add_task(phrase, total=steps)

        for _ in range(steps):
            time.sleep(0.05)
            progress.update(task, advance=1)


def charge_6(duration, steps = 100, phrase = None, bar_width = None, time_show = True):
    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(bar_width=bar_width),
        TimeRemainingColumn(),
    ) as progress:
        phrase = phrase.ljust(40)
        task = progress.add_task(phrase, total=steps)

        for _ in range(steps):
            time.sleep(0.05)
            progress.update(task, advance=1)