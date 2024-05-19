from unittest import result
import modules.scripts as scripts
import gradio as gr
from pprint import pprint
import os
import math
from PIL import Image, ImageFont, ImageDraw, ImageColor, PngImagePlugin
from PIL import Image
import imageio
import random
import numpy as np
import re


from modules.processing import process_images
from modules.shared import cmd_opts, total_tqdm, state
from scripts.regions import KEYBRK

class Script(scripts.Script):

    def __init__(self):
        self.count = 0
        self.latent = None
        self.latent_hr= None

    def title(self):
        return "DiffReprom"

    def ui(self, is_img2img):
        with gr.Row():
            pass
            # urlguide = gr.HTML(value = fhurl(GUIDEURL, "Usage guide"))
        with gr.Row():
            # mode = gr.Radio(label="Divide mode", choices=["Horizontal", "Vertical","Mask","Prompt","Prompt-Ex"], value="Horizontal",  type="value", interactive=True)
            #outmode = gr.Radio(label="Output mode", choices=["ALL", "Only 2nd"], value="ALL",  type="value", interactive=True)
            #changes = gr.Textbox(label="original, replace, replace ;original, replace, replace...")
            pass
        with gr.Row(visible=True):
            # ratios = gr.Textbox(label="Divide Ratio",lines=1,value="1,1",interactive=True,elem_id="RP_divide_ratio",visible=True)
            options = gr.CheckboxGroup(choices=["Reverse"], label="Options",interactive=True,elem_id="RP_usecommon")
            addout = gr.CheckboxGroup(choices=["mp4","Anime Gif"], label="Additional Output",interactive=True,elem_id="RP_usecommon")
        with gr.Row(visible=True):
            step = gr.Slider(label="Step", minimum=0, maximum=150, value=4, step=1)
            duration = gr.Slider(label="FPS", minimum=1, maximum=100, value=30, step=1)
            thdecrease = gr.Slider(label="Threshold Decrease", minimum=0, maximum=0.05, value=0, step=0.001)
            batch_size = gr.Slider(label="Batch Size", minimum=1, maximum=8, value=1, step=1,visible = False)
        with gr.Blocks(visible=True):
            with gr.Tab("Batch count") as tabcount:
                seedcount = gr.Number(show_label=False, value=1, precision=0, interactive=True)
            with gr.Tab("Seeds") as tabseeds:
                seedselect = gr.Textbox(show_label=False, value="", interactive=True)
            with gr.Tab("Plus seeds") as tabplus:
                seedplus = gr.Textbox(show_label=False, value="", interactive=True)
            seedmode = gr.Textbox(value = "Batch count",visible = False)
            tabcount.select(lambda :"Batch count", None, seedmode)
            tabseeds.select(lambda :"Seeds", None, seedmode)
            tabplus.select(lambda :"Plus seeds", None, seedmode)
        with gr.Row(visible=True):
            plans = gr.TextArea(label="Schedule")
        with gr.Row(visible=True):
            mp4pathd = gr.Textbox(label="mp4 output directory")
            mp4pathf = gr.Textbox(label="mp4 output filename")
        with gr.Row(visible=True):
            gifpathd = gr.Textbox(label="Anime gif output directory")
            gifpathf = gr.Textbox(label="Anime gif output filename")

        return [options, duration, plans, step, addout, batch_size, mp4pathd, mp4pathf, gifpathd, gifpathf, thdecrease, seedmode, seedcount, seedselect, seedplus]

    def run(self, p, options, duration, plans, step, addout, batch, mp4pathd, mp4pathf, gifpathd, gifpathf, thdecrease, seedmode, seedcount, seedselect, seedplus):
        self.__init__()

        p.rps_diff = True

        p.extra_generation_params.update({
                    "RPS Base Prompt":p.prompt.split(KEYBRK)[0],
                    "RPS Schedule":plans,
                })
        plans = plans.splitlines()
        plans = [f.split(";") for f in plans]
        plannum = 1 
        while plannum < len(plans):
            if isregion(plans[plannum][0]):
                plans[plannum-1].extend(plans[plannum])
                del plans[plannum]
            else:
                plannum += 1
        all_prompts = []
        all_prompts_hr = []
        rcount=1
        p.thdecrease = []
        p.thstep = []
        lastth=""

        base_prompt = p.prompt.split(KEYBRK)[0]
        base_prompt = base_prompt + " BREAK"
        base_prompt_origin = base_prompt
        base_prompt_p=base_prompt
        i=0
        while i < len(base_prompt_p) - 1:
            if base_prompt_p[i] == '$' and base_prompt_p[i+1] == '{':
                kcount=1
                ecount=0
                j = i + 2
                while j < len(base_prompt_p):
                    if base_prompt_p[j] == '{':kcount=kcount+1
                    if base_prompt_p[j] == '}':kcount=kcount-1
                    if base_prompt_p[j] == '=' and kcount == 1 :ecount=1
                    if kcount <= 0: break
                    j = j + 1
                if kcount <= 0 and ecount == 1:
                    base_prompt_p = base_prompt_p[:i]+base_prompt_p[j + 1:]
                else: i = i + 1
            else: i = i + 1
        base_prompt_p = re.sub("<lora.*?>", "", base_prompt_p)
        base_prompt_p = re.sub("<lyco.*?>", "", base_prompt_p)
        base_prompt_p_origin = base_prompt_p

        def makesubprompt(pro, tar, wei, ste):
            a = "" #if tar in base_prompt else tar
            if pro == "": return f" {KEYBRK} ,{tar}"
            if int(ste) <= p.steps:
                ste = str(math.ceil(int(ste) / p.steps * 1000) / (1000))
            else:
                ste = str(1 + math.ceil((int(ste) - p.steps) / p.hr_second_pass_steps * 1000) / (1000))
            if wei == 1:
                return f"{a} {KEYBRK} {base_prompt_p} [:{pro}:{ste}], {tar}"
            else:
                return f"{a} {KEYBRK} {base_prompt_p} [:({pro}:{wei}):{ste}], {tar}" 

        def makesubprompt_hr(pro, tar, wei, ste):
            a = "" if tar in base_prompt else tar
            if pro == "": return f" BREAK ,{tar}" 
            if wei == 1:
                return f"{a} BREAK {base_prompt} {pro}, {tar}"
            else:
                return f"{a} BREAK {base_prompt} ({pro}:{wei}), {tar}" 
        #pprint(plans)

        for plan in plans:
            base_prompt = base_prompt_origin
            base_prompt_p = base_prompt_p_origin
            rparas = []
            if 3 > len(plan):
                sets = plan[0]
                if "=" in sets:
                    change, num = sets.split("=")
                    if change == "r":
                        rcount = int(num)
                    if change == "step":
                        step = int(num)
                    if "th" in change:
                        all_prompts.append(["th",num])
                        all_prompts_hr.append(None)
                        lastth=num
                elif "*" in sets:
                    num = int(sets.replace("*",""))
                    thstep = [-1] * rcount
                    thd = [None] * rcount
                    all_prompts.extend([["th",2]]+[["thstep",thstep]]+[["thd",thd]]+[base_prompt + "." + (" " + KEYBRK + " " + base_prompt_p  + f" ,.") * rcount]*num + [["th",None]])
                    all_prompts_hr.extend([["th",2]]+[["thstep",thstep]]+[["thd",thd]]+[base_prompt + "." + (" " + KEYBRK + " " + base_prompt_p  + f" ,.") * rcount]*num + [["th",None]])
                elif "ex-on" in sets:
                    strength = float(sets.split(",")[1]) if "," in sets else None
                    all_prompts.append(["ex-on",strength])
                    all_prompts_hr.append(None)
                elif "ex-off" in sets:
                    all_prompts.append(["ex-off"])
                    all_prompts_hr.append(None)
                elif sets == "0":
                    thstep = [-1] * rcount
                    thd = [None] * rcount
                    all_prompts.extend([["th",2],["thstep",thstep],["thd",thd], base_prompt + "." + (" " + KEYBRK + " " + base_prompt_p  + f" ,.") * rcount, ["th",None]])
                    all_prompts_hr.extend([["th",2],["thstep",thstep],["thd",thd], base_prompt + "." + (" " + KEYBRK + " " + base_prompt_p  + f" ,.") * rcount, ["th",None]])
                continue
            for pos in range(-1, len(plan)):
                if pos == -1 or (pos == 0 and plan[0].startswith("%")) or isregion(plan[pos]):
                    if(pos >= 0 and "%p" in plan[pos]):
                        base_prompt=base_prompt.replace(plan[pos+1], plan[pos+2])
                        base_prompt_p=base_prompt_p.replace(plan[pos+1], plan[pos+2])
                        continue
                    if(pos == -1 and plan[0].startswith("%")):
                        continue
                    ipro = "" if pos == -1 else plan[pos]
                    iweight = "1"
                    istep = str(step)
                    ithd = thdecrease
                    if pos + 3 < len(plan) and not isregion(plan[pos+3]) and plan[pos+3] != "":
                        iweight = plan[pos+3]
                        if pos + 4 < len(plan) and not isregion(plan[pos+4]) and plan[pos+4] != "":
                            istep = plan[pos+4]
                            if pos + 5 < len(plan) and not isregion(plan[pos+5]) and plan[pos+5] != "":
                                ithd = plan[pos+5]
                    rparas.append([ipro, plan[pos+1], plan[pos+2], iweight, istep, ithd])
            if len(rparas)>0:
                targettype = "weight"
                targets = parse_weights(rparas[0][3])
                istep = step
                asteps = parse_steps(rparas[0][4])
                if type(asteps) is list:
                    targettype = "step"
                    targets = asteps
                else:
                    istep=asteps
                for target in targets:
                    thd = []
                    for rpara in rparas:
                        thd.append(float(rpara[5]))
                    while len(thd) < rcount:
                        thd.append(0)
                    thstep = []
                    for rpara in rparas:
                        if targettype == "step":
                            thstep.append(int(target))
                        else:
                            thstep.append(int(rpara[4]))
                    while len(thstep) < rcount:
                        thstep.append(9999)
                    for rpara in rparas:
                        if "%ap" in rpara[0]:
                            base_prompt = base_prompt.rstrip(" BREAK") + ", " + rpara[2] + " BREAK"
                    editprompt = base_prompt
                    editprompt_hr = base_prompt
                    for rpara in rparas:
                        if rpara == rparas[0]:
                            if targettype == "step":
                                editprompt += makesubprompt(rparas[0][1], rparas[0][2], rparas[0][3], target)
                            elif targettype == "weight":
                                editprompt += makesubprompt(rparas[0][1], rparas[0][2], target, istep)
                        else:
                            editprompt += makesubprompt(rpara[1], rpara[2], rpara[3], rpara[4])
                    if len(rparas)<rcount:
                        for count in range(rcount - len(rparas)):
                            editprompt += (" " + KEYBRK + " " + base_prompt_p  + f" ,.")
                            editprompt_hr += (" " + KEYBRK + " " + base_prompt_p  + f" ,.")
                    all_prompts.extend([["thstep",thstep],["thd",thd],editprompt])
                    all_prompts_hr.extend([["thstep",thstep],["thd",thd],editprompt])
                continue

        #pprint(all_prompts)

        results = {}
        output = None
        index = []
        all_prompt_opt=[]
        promptth = "thNone"
        promptths = ""
        promptthd = ""

        for prompt in all_prompts:
            if type(prompt) == list:
                if prompt[0] == "th":
                    promptth = "th" + str(prompt[1])
                if prompt[0] == "thstep":
                    promptths = ",".join(map(str,prompt[1]))
                if prompt[0] == "thd":
                    promptthd = ",".join(map(str,prompt[1]))
                all_prompt_opt.append("")
                continue
            propmt_joind = promptth + promptths + promptthd + prompt
            all_prompt_opt.append(propmt_joind)
            if (propmt_joind) not in results.keys():
                results[propmt_joind] = None
                #print(propmt_joind)

        print(f"DiffReprom Start")
        print(f"FPS = {duration}, {len(all_prompts)} frames, {round(len(all_prompts)/duration,3)} Sec")

        seeds = []

        if p.seed == -1 : p.seed = int(random.randrange(4294967294))

        if seedmode == "Batch count":
            seeds = list(range(p.seed, p.seed + seedcount, 1))
        if seedmode == "Seeds":
            seeds = [int(s) for s in seedselect.split(",")]
        if seedmode == "Plus seeds":
            seeds = [int(s) + p.seed for s in seedplus.split(",")]

        job = math.ceil((len(results) * len(seeds)))

        allstep = job * p.steps
        total_tqdm.updateTotal(allstep)
        state.job_count = job

        for seed in seeds:
            p.seed = seed
            for key in results:
                results[key] = None

            for prompt, prompt_hr, prompt_opt in zip(all_prompts,all_prompts_hr,all_prompt_opt):
                if type(prompt) == list:
                    if prompt[0] == "th":
                        p.threshold = prompt[1]
                    if prompt[0] == "thstep":
                        p.thstep = prompt[1]
                    if prompt[0] == "thd":
                        p.thdecrease = prompt[1]
                    if prompt[0] == "ex-on":
                        p.seed_enable_extras = True
                        p.subseed_strength = strength if prompt[1] else 0.1
                    if prompt[0] == "ex-off":
                        p.seed_enable_extras = False
                    continue
                if results[prompt_opt] is not None:
                    continue
                p.prompt = prompt
                p.hr_prompt = prompt_hr

                processed = process_images(p)
                results[prompt_opt] = processed.images[0]
                if output is None :output = processed
                else:output.images.extend(processed.images)


            all_result = []

            for prompt_opt in all_prompt_opt:
                if prompt_opt == "": continue
                all_result.append(results[prompt_opt])

            if "Reverse" in options: all_result.reverse()

            outpath = p.outpath_samples
            if "Anime Gif" in addout:
                if gifpathd != "": outpath = os.path.join(outpath,gifpathd)

                try:
                    os.makedirs(outpath)
                except FileExistsError:
                    pass

                if gifpathf == "": gifpathf = "dfr"

                gifpath = gifpath_t = os.path.join(outpath, gifpathf + ".gif")
                
                is_file = os.path.isfile(gifpath)
                j = 1
                while is_file:
                    gifpath = gifpath_t.replace(".gif",f"_{j}.gif")
                    is_file = os.path.isfile(gifpath)
                    j = j + 1

                all_result[0].save(gifpath, save_all=True, append_images=all_result[1:], optimize=False, duration=(1000 / duration), loop=0)

            outpath = p.outpath_samples
            if "mp4" in addout:
                if mp4pathd != "": outpath = os.path.join(outpath,mp4pathd)
                if mp4pathf == "": mp4pathf = "dfr"
                mp4path = mp4path_t = os.path.join(outpath, mp4pathf + ".mp4")

                try:
                    os.makedirs(outpath)
                except FileExistsError:
                    pass

                is_file = os.path.isfile(mp4path_t)
                j = 1
                while is_file:
                    mp4path = mp4path_t.replace(".mp4",f"_{j}.mp4")
                    is_file = os.path.isfile(mp4path)
                    j = j + 1

                numpy_frames = [np.array(frame) for frame in all_result]

                with imageio.get_writer(mp4path, fps=duration) as writer:
                    for numpy_frame in numpy_frames:
                        writer.append_data(numpy_frame)

            self.__init__()
        return output

    def settest1(self,valu):
        self.test1 = valu

def isregion(s):
    rword = s.replace("-","")
    return "-" in s and (rword == "" or rword[0] == "%")

def parse_steps(s):
    if "(" in s:
        step = s[s.index("("):]
        s = s.replace(step,"")
        step = int(step.strip("()"))
    else:
        step = 1

    if "-" in s:
        start,end = s.split("-")
        start,end = int(start), int(end)
        step = step if end > start else -step
        return list(range(start, end + step, step))
    
    if "*" in s:
        w, m = s.split("*")
        if w == "": w = 4
        return [w] * int(m)
    
    return int(s)

def parse_weights(s):
    if s == "": return[1]
    if "*" in s:
        w, m = s.split("*")
        if w == "": w = 1
        return [w] * int(m)

    if '(' in s:
        step = s[s.index("("):]
        s = s.replace(step,"")
        step = float(step.strip("()"))
    else:
        step = None

    out = []

    if "-" in s:
        rans = [x for x in s.split("-")]
        if step is None:
            digit = len(rans[0].split(".")[1])
            step = 10 ** -digit
        rans = [float(r) for r in rans]
        for start, end in zip(rans[:-1],rans[1:]):
            #print(start,end)
            sign = 1 if end > start else -1
            now = start
            for i in range(int(abs(end-start)//step) + 1):
                out.append(now)
                now = now + step * sign
    else:
        out =[float(s)]

    if out == []:out = [1]
    out = [round(x, 5) for x in out]
    return out