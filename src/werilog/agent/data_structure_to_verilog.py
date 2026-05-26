import os
import sys
import time
import subprocess
from google import genai
from pathlib import Path
from google.genai.errors import ClientError
from tenacity import (
    retry,
    wait_fixed,
    stop_after_attempt,
    retry_if_exception_type,
)


# Gemini api 1 min 5 request limit, so retry if hit the limit
def print_retry_info(retry_state):
    print(
        f" Try {retry_state.attempt_number} times failure。 "
        f"Retry after{retry_state.next_action.sleep:.2f} seconds",
        file=sys.stderr,
    )


# wait for 30s second per request
SLEEP_TIME = 30


@retry(
    wait=wait_fixed(SLEEP_TIME),
    stop=stop_after_attempt(10),
    retry=retry_if_exception_type(ClientError),
    reraise=True,
    before_sleep=print_retry_info,
)
def gen_verilog(path, count):
    with open(path, "r") as file:
        data_structure = file.read()

    prompt = f"""
    Please change the node datastructure to equivalent verilog code. Only output verilog code.
    {data_structure}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    answer = response.text
    lines = answer.splitlines()
    final_answer = "\n".join(lines[1:-1])

    file_name = path.name
    dir_name = path.parent.name
    dir_path = AGENT_VERILOG / dir_name
    file_path = dir_path / file_name
    new_file_path = file_path.with_suffix(".v")

    dir_path.mkdir(exist_ok=True)
    new_file_path.touch(exist_ok=True)

    with open(new_file_path, "w") as f:
        f.write(final_answer)
        print(f"TEST {count}-th : Saved agent generated file at {new_file_path}.")


def gen_verilog_traversal():
    count = 0
    for path in sorted(DATA_STRUCTURE.iterdir()):
        if path.is_dir():
            for file in sorted(path.iterdir()):
                if file.is_file() and file.suffix == ".yaml":
                    time.sleep(SLEEP_TIME)
                    count += 1
                    gen_verilog(file, count)


def testbench(path, count):
    file_name = path.name
    short_file_name = path.name[8:]
    dir_name = path.parent.name

    # ai_file
    ai_dir_path = AGENT_VERILOG / dir_name
    ai_file_path = ai_dir_path / file_name
    ai_new_file_path = ai_file_path.with_suffix(".v")

    # gt_file
    gt_dir_path = VERILOG / dir_name
    gt_file_path = gt_dir_path / short_file_name
    gt_new_file_path = gt_file_path.with_suffix(".v")

    # testbench file
    tb_dir_path = TESTBENCH / dir_name
    tb_file_path = tb_dir_path / short_file_name
    tb_new_file_path = tb_file_path.with_suffix(".v")

    # output file
    temp = PROJECT_ROOT / "temp.vvp"

    compile_cmd = [
        "iverilog",
        "-o",
        str(temp),
        str(tb_new_file_path),
        str(ai_new_file_path),
        str(gt_new_file_path),
    ]

    compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if compile_result.returncode != 0:
        print(f"[TEST {count}]\n {compile_result.stderr}Result : fail\n")
        return False
    run_cmd = ["vvp", str(temp)]
    run_result = subprocess.run(run_cmd, capture_output=True, text=True)
    print(f"[TEST {count}]")
    print(run_result.stdout)
    # remove output_file
    os.remove(str(temp))

    return any(
        line.strip() == "Result : success" for line in run_result.stdout.splitlines()
    )


def testbench_traversal():
    count = 0
    fail_cnt = 0
    success_cnt = 0
    for path in sorted(DATA_STRUCTURE.iterdir()):
        if path.is_dir():
            for file in sorted(path.iterdir()):
                if file.is_file() and file.suffix == ".yaml":
                    count += 1
                    if testbench(file, count):
                        success_cnt += 1
                    else:
                        fail_cnt += 1
    print(f"Total result : {success_cnt}/{success_cnt + fail_cnt}\n")


if __name__ == "__main__":
    # load GEMINI
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # file path
    CURRENT_FILE = Path(__file__).resolve()
    PROJECT_ROOT = CURRENT_FILE.parent.parent.parent
    DATASET = PROJECT_ROOT / "dataset"
    DATA_STRUCTURE = DATASET / "example-data-structure"
    VERILOG = DATASET / "example-verilog"
    TESTBENCH = DATASET / "example-verilog-testbench"
    AGENT_VERILOG = PROJECT_ROOT / "agent_output" / "data-structure-to-verilog"

    # ai generate verilog code
    gen_verilog_traversal()

    # verify ai code
    testbench_traversal()
