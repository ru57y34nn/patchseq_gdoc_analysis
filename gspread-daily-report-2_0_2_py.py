import json
import fnmatch
import os
import numpy as np
import pandas as pd
from pandas.io.json import json_normalize
from pandas.tseries.offsets import CustomBusinessDay
from pandas.tseries.holiday import USFederalHolidayCalendar
from tkFileDialog import askdirectory
from datetime import datetime, timedelta
import collections


def get_similar_values(invalid_val, valid_vals):
    '''Look for valid values that start with the first letter of user entry'''
    if len(invalid_val) > 0:
        first = invalid_val[0]
        result = [v for v in valid_vals if v.startswith(first)]
    else:
        result = []
    return result

def get_response_to_invalid(invalid_val, valid_vals):
    '''Return a non-specific error message, or similar valid values if they exist'''
    similar = get_similar_values(invalid_val, valid_vals)
    if len(similar) > 0:
        response = "\nPerhaps you meant one of the following? \n%s " %similar
    else:
        response = "\nHmm, please try again..."
    return response

def validated_input(prompt_text, invalid_response, valid_options=None):
    '''Keep asking user for input until a valid input has been entered'''
    while True:
        result = raw_input(prompt_text)
        result = result.lower()
        if (valid_options) and (result not in valid_options):
            response = get_response_to_invalid(result, invalid_response, valid_options)
            print response
            continue
        else:
            break
    return result

def validated_date_input(prompt_text, invalid_response, valid_options=None):
    """Prompt user to enter date, and check whether date is valid input.
    Keep prompting until a valid input has been entered.
    
    Parameters
    ----------
    prompt_text : string
    invalid_response : string
        A message to return to user if entry was invalid.
    valid_options: None or list
        Optional argument with valid options
        
    Returns
    -------
    result : string
        User's validated response to prompt text.
    """

    while True:
        result = raw_input(prompt_text)
        result = result.lower()
        try:
            datetime.strptime(result, "%y%m%d")
        except:
            response = get_response_to_invalid(result, invalid_response, valid_options)
            print response
            continue
        else:
            break
    return result

def get_directory(expt):
    if expt == "n":
    	DIRNAME = r'\\allen\programs\celltypes\workgroups\279\Patch-Seq\all-metadata-files'    	#"//allen/programs/celltypes/workgroups/279/MIES experiments
    elif expt == "y":
        DIRNAME = askdirectory()
    return DIRNAME


def get_jsons(dirname, expt, delta_days):
    """Return filepaths of metadata files that were created within
    delta_days of today.
    
    Parameters
    ----------
    dirname : string
        Path to metadata file directory.
    expt : string
        Experiment type for filename match ("PS" or "IVSCC").
    delta_days : int
        A number of days in the past.

    Returns
    -------
    json_paths : list
        A list of filepaths that are a expt string match and were
        created within delta_days of today.
    """

    json_files = []; json_paths = []
    comparison_date = datetime.today()
    
    for jfile in os.listdir(dirname):
        if fnmatch.fnmatch(jfile,'*.%s.json' %expt):
            jpath = os.path.join(dirname, jfile)
            created_date = datetime.fromtimestamp(os.path.getctime(jpath))
            if abs((comparison_date - created_date ).days) < delta_days:
                json_files.append(jfile)
                json_paths.append(os.path.join(dirname, jfile))
    return json_files, json_paths


def get_spec_name(data):
    name = data['limsSpecName']
    name = name.replace(' ', '')
    return name  
    
def generate_cell_id(cell_num, data):
    '''Generate LIMS cell ID from specimen (slice) ID'''
    cell_num += 1
    if cell_num < 10:
            cell_id = "%s%s%s" % (get_spec_name(data), '.0', str(cell_num))
    else:
            cell_id = "%s%s%s" % (get_spec_name(data), '.', str(cell_num))
    return cell_num, cell_id
    
    
def get_PS_ephys_state(attempt):
    '''Return spreadsheet-formatted value for ephys state'''
    ephys_dict = {'FAILURE':'', 'SUCCESS (high confidence)':'x', 'SUCCESS (low confidence)':'?', 'SUCCESS': 'x'}
    result = ephys_dict[attempt['status']]
    return result

def format_date(dt):
    '''Get a formatted YYMMDD string from datetime object'''
    dt = dt.replace(' ', '/') 
    x = dt.split('/')
    date_str = x[2][2::] + x[0] + x[1]
    if len(x) == 4:
        time = x[3]
    else:
        time = None
    return date_str, time

def get_format_acsf_date(slice_info):
    d = get_if_exists(slice_info, 'acsfProductionDate')
    if  d == '':
        d_fmt =  ''
    else:
        x = d.split('/')
        d_fmt = x[2] + x[0] + x[1]
    return d_fmt

def is_float(val):
    try:
        float(val)
        return True
    except ValueError:
        return False

def get_if_exists(d, k):
    '''Get item if given field exists in the JSON'''
    if k in d.keys():
        val = d[k]
        if is_float(val):
            result = float(val)
        else:
            result = val
    else:
        result = ''
    return result

def get_user(slice_info, p_users, expt):
    if slice_info['rigOperator'] == "**Other**":
        user = get_if_exists(slice_info, "otherRigOperator")
    else:
        user = slice_info['rigOperator']
        
    if expt == 'p':
        if user in p_users:
            user = p_users[user]
        else:
            user = 'P?'
    return user

def get_PS_region(app_info, loc_dict):
    ''' Standardize output of anatomical location field'''
    loc = get_if_exists(app_info, 'anatomicalLocation')
    if loc in loc_dict.keys():
        loc = loc_dict[loc]
    return loc

def get_PS_pilot(app_info):
    '''Return pilot name, if not Patch-Seq, which was an early placeholder'''
    pilot_name = get_if_exists(app_info, 'pilotName')
    if pilot_name != "Patch-Seq":
        result = pilot_name
    else:
        result = ''
    return result

def get_PS_pilot_deets(app_info):
    '''Find the field with pilot details, and return contents'''
    fields = app_info.keys()
    pilot_keys = [k for k in fields if k.startswith("pilotTest")]
    if len(pilot_keys) > 0:
        result = app_info[pilot_keys[0]]
    else:
        result = ''
    return result

def format_time(str_t):
    '''Reformat time'''
    t= datetime.strptime(str_t, '%H:%M:%S')
    if t.minute >= 10:
        fmt_t = '%d%d' %(t.hour, t.minute)
    else:
        fmt_t = '%d0%d' %(t.hour, t.minute)
    return fmt_t

def get_time(data_dict, time_name):
    '''Check if the time info exists, then reformat to datetime'''
    time_str = get_if_exists(data_dict, time_name)
    if time_str != '':
        time= datetime.strptime(data_dict[time_name], '%H:%M:%S')
    else:
        time = '' 
    return time

def calculate_tdelta(t1, t2):
    '''Return formatted time difference MM:SS'''
    if t1 != '' and t2 != '':
        d = t2 - t1
        if d.days < 0:
            d_fmt_1 = 'error in time entry'
            d_fmt_2 = np.nan
        else:
            d_min = d.seconds / 60
            d_sec = d.seconds % 60
            d_fmt_1 = np.where(d_sec >= 10,'%d:%d' %(d_min, d_sec), '%d:0%d' %(d_min, d_sec))
            d_fmt_2 = d.seconds / 60.
    else:
        d_fmt_1 = ''
        d_fmt_2 = np.nan
    return d_fmt_1, d_fmt_2
        

def get_durations(cell_info):
    '''Where possible, calculate durations between times.
    Format 1 is MM:SS, Format 2 is MM.(SS/60)'''  
    rec_info = cell_info['recording']
    ext_info = cell_info['extraction']
    #sol_info = cell_info[]

    start_time = get_time(rec_info, 'timeStart')
    wc_start_time =  get_time(rec_info, 'timeWholeCellStart')   
    ext_start_time = get_time(ext_info, 'timeExtractionStart')
    ext_end_time = get_time(ext_info, 'timeExtractionEnd')
    ret_start_time = get_time(ext_info, 'timeRetractionStart')
    ret_end_time = get_time(ext_info, 'timeRetractionEnd')
    
    tdelta_to_wc_fmt_1, tdelta_to_wc_fmt_2 = calculate_tdelta(start_time, wc_start_time)
    tdelta_ext_fmt_1, tdelta_ext_fmt_2 = calculate_tdelta(ext_start_time, ext_end_time)
    tdelta_ret_fmt_1, tdelta_ret_fmt_2 = calculate_tdelta(ret_start_time, ret_end_time)
    tdelta_rec_fmt_1, tdelta_rec_fmt_2 = calculate_tdelta(wc_start_time, ret_end_time)

    
    return start_time, tdelta_to_wc_fmt_2, tdelta_ext_fmt_2, tdelta_ret_fmt_2 ,tdelta_rec_fmt_2
    

def generate_PS_lims_tube_id(user, date, tube_id):
    '''Generate LIMS tube ID from user, date and tube ID'''
    if tube_id != '':
        slice_date, slice_time = format_date(date)
        try:
            tube_str = str(int(tube_id))
        except:
            return np.nan
            
        if len(tube_str) == 2:
            tube_str = '0' + tube_str
        elif len(tube_str) == 1:
            tube_str = '00' + tube_str
        else:
            tube_str = tube_str  
        lims_tube_id = '%sS4_%s_%s_A01' %(user, slice_date, tube_str)
    else:
        lims_tube_id = ''
    return lims_tube_id


def extract_PS_info(json_paths, p_users, loc_dict):
    dates = []; users = []; files = []; ephys = []; cell_types = []; start_times = []; times_to_wc = []; anat_locs = []; layers = []; slice_ids = []; locs = []; e_pressures = []; r_pressures = []; patches = []; pipette_r = []; nucleus_suck = []; vols = []; notes = []; extraction_durations = []; retraction_durations = []; patch_durations = []; rheos = []; pip_sizes = []; vm_s = []; access_rs = []; ephys_notes = []; internal_vs = []; rnase_inh_concs = []; biocytin_concs = []; alexa_concs = []; tube_ids = []; well_ids = []; lims_tube_ids = []; rig_nums = []; pilots = []; pilot_deets = []; slice_times = []; slice_healths = []; acsf_dates = []; slice_notes = []; depths = [];
    tdt_dict = {'Cre+':'tdt+', 'Cre-':'tdt-', 'human':'human'}
    expt = 'p'
    for json_path in json_paths:
        with open(json_path) as data_file:    
            slice_info = json.load(data_file)
            formv = get_if_exists(slice_info, "formVersion")# slice_info["formVersion"]
            pip_key = [k for k in slice_info.keys() if k.startswith('pipettes')][0]
            cell_num = 0      
            for num, cell_info in enumerate(slice_info[pip_key]):
                if cell_info['status'] != 'FAILURE':
                    cell_num, cell_id = generate_cell_id(cell_num, slice_info)
                    slice_date, slice_time = format_date(slice_info['date'])
                    dates.append(slice_date)
                    acsf_dates.append(get_format_acsf_date(slice_info))
                    slice_times.append(slice_time)
                    slice_ids.append(get_spec_name(slice_info))
                    user = get_user(slice_info, p_users, expt)
                    users.append(user)
                    rig_nums.append(get_if_exists(slice_info, 'rigNumber'))
                    files.append(cell_id)
                    ephys.append(get_PS_ephys_state(cell_info))
                    
                    start_time, tdelta_to_wc, tdelta_ext, tdelta_ret, tdelta_rec = get_durations(cell_info)
                    if isinstance(start_time, datetime):
                        start_time = start_time.time().strftime("%H:%M")
                    start_times.append(start_time)
                    times_to_wc.append(tdelta_to_wc)
                    extraction_durations.append(tdelta_ext)
                    retraction_durations.append(tdelta_ret)
                    patch_durations.append(tdelta_rec)
                    
                    app_info = cell_info['approach']
                    #sol_info = cell_info['internalSolution']
                    rec_info = cell_info['recording']
                    ext_info = cell_info['extraction']
                    
                    slice_healths.append(app_info['sliceHealth'])
                    depths.append(get_if_exists(app_info, 'depth'))
                    locs.append(get_if_exists(app_info, 'detailedLocation'))
                    pilots.append(get_PS_pilot(app_info))
                    pilot_deets.append(get_PS_pilot_deets(app_info))
                    if formv < "1.0.8": #When corticalLayer was replaced as a field
                        anat_locs.append(get_PS_region(app_info, loc_dict))
                        layers.append(get_if_exists(app_info, 'corticalLayer'))
                    else:
                        if formv == "2.0.0":
                            try: 
                                roi = app_info['manualRoi']
                            except KeyError:
                                try:
                                    roi = app_info['autoRoi']
                                except KeyError:
                                    roi = 'None'
                        else:
                            roi = app_info['anatomicalLocation']
                        if roi == 'None':
                            anat_locs.append('None')
                            layers.append('None')
                        else:
                            anat_locs.append(roi.split(",")[0])
                            layers.append(roi.split(",")[1].split(" ")[-1])
       
                    '''
                    internal_vs.append(get_if_exists(sol_info,'version'))                
                    rnase_inh_concs.append(get_if_exists(sol_info,'concentrationRnaseInhibitor'))
                    biocytin_concs.append(get_if_exists(sol_info,'concentrationBiocytin'))
                    alexa_concs.append(get_if_exists(sol_info,'concentrationAlexa'))
                    '''

                    #vols.append(get_if_exists(sol_info, 'volume'))              
                    pip_sizes.append(get_if_exists(rec_info,'pipetteR'))
                    access_rs.append(get_if_exists(rec_info,'accessR'))
                    vm_s.append(get_if_exists(rec_info,'membraneV'))
                    rheos.append(get_if_exists(rec_info,'rheobase'))

                    cre_line = tdt_dict[app_info['creCell']]
                    human_cell = get_if_exists(rec_info,'humanCellTypePrediction')
                    if cre_line != 'human':
                        cell_types.append(tdt_dict[app_info['creCell']])
                    else:
                        cell_types.append(human_cell)              
                                     
                    ephys_notes.append(get_if_exists(cell_info,'successNotes')+ "   " + get_if_exists(cell_info,'qcNotes'))

                    e_pressures.append(get_if_exists(ext_info, 'pressureApplied'))
                    r_pressures.append(get_if_exists(ext_info, 'retractionPressureApplied'))
                    patches.append(get_if_exists(ext_info, 'postPatch'))
                    pipette_r.append(get_if_exists(ext_info, 'endPipetteR'))
                    nucleus_suck.append(get_if_exists(ext_info, 'nucleus'))

                    notes.append(str(get_if_exists(ext_info, 'extractionObservations'))+ "   " + str(get_if_exists(ext_info, 'sampleObservations'))+"  " +str(get_if_exists(ext_info, 'extractionNotes')))

                    slice_notes.append(get_if_exists(slice_info, 'sliceNotes'))
                    well_ids.append(get_if_exists(slice_info, 'wellID'))      
                    tube_id = get_if_exists(ext_info, 'tubeID')
                    tube_ids.append(tube_id)
                    lims_tube_id = generate_PS_lims_tube_id(user, slice_info['date'], tube_id)
                    lims_tube_ids.append(lims_tube_id)
    empty_cells = [''] * len(files)
    ps_d = collections.OrderedDict([('', empty_cells), ('Date', dates), ('User', users), ('Rig #', rig_nums), ('File', files), ('Ephys', ephys), 
                                    ('Trans', empty_cells), ('Morph', empty_cells), ('Pilot', pilots), ('Pilot Details', pilot_deets), 
                                    ('cell type', cell_types), ('Slice on Rig Time', slice_times), ('Approach Time', start_times), 
                                    ('Time to whole-cell', times_to_wc), ('Region', anat_locs), ('Layer', layers), ('Depth (um)', depths), 
                                    ('Slice (Lims ID?)', slice_ids), ('Slice Health', slice_healths), ('Slice Notes', slice_notes), 
                                    ('Location (x,y coordinates?)', locs), ('extraction pressure applied (mbar)', e_pressures), 
                                    ('retraction pressure applied (mbar)', r_pressures), ('Post patch?', patches), ('Post patch pipette R', pipette_r), ('Nucleus sucked in?', nucleus_suck),
                                    ('Notes', notes), ('Time spent extracting cytosol', extraction_durations), ('Time spent retracting pipette', retraction_durations), 
                                    ('patch duration', patch_durations), 
                                    ('Ephys Protocol', empty_cells), ('Rheobase', rheos), ('Pipette size (MO)', pip_sizes), ('Vm', vm_s), 
                                    ('Breakin Ra', access_rs), ('Ephys notes', ephys_notes), ('ACSF Date', acsf_dates), 
                                    ('Tube_ID', tube_ids), ('Well ID #', well_ids), 
                                    ('Lims tube id', lims_tube_ids)])
    p_df = pd.DataFrame.from_dict(ps_d)
    p_df.sort_values(by=['Date','User','Slice on Rig Time'], ascending=True, inplace=True)
    return p_df

def make_PS_xlsx(DIRNAME,SPREADNAME, df, c):
    '''Format data as closely as possible to Patch-Seq Spreadsheet'''
    writer = pd.ExcelWriter(os.path.join(DIRNAME, SPREADNAME), engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='metadata')
    book  = writer.book
    sheet = writer.sheets['metadata']
    n = len(df)
    cols = ["B1:E{}", "F2:F{}", "G1:J{}", "K1:U{}", "V1:AA{}", "AB1:AH{}", "AI1:AL{}", "AM1:AM{}", "AN1:AN{}", "AO1:AO{}"]
    fmt_ranges = [col.format(n + 1) for col in cols]
    bg_colors = [0, 0, 0, c[0], c[1], c[2], c[3], c[4], c[5], c[4]]
    widths = [15, 6, 10, 10, 10, 10, 10, 10, 10, 10]
    
    cond_range = "K2:K{}".format(n+1) 
    tdtP_fmt = book.add_format({'font_name':'Arial', 'font_size':10, 'align':'center', 'font_color':'red', 'bold':True, 'bg_color':c[0]})
    tdtP = {'type':'cell', 'criteria':'==', 'value':'"tdt+"', 'format':tdtP_fmt}
    tdtN_fmt = book.add_format({'font_name':'Arial', 'font_size':10, 'align':'center', 'font_color':'black', 'bold':True,'bg_color':c[0]})
    tdtN = {'type':'cell', 'criteria': '==', 'value':'"tdt-"', 'format':tdtN_fmt}

    for i, r in enumerate(fmt_ranges):
        if i == 1:
            col_fmt = book.add_format({'font_name':'Arial', 'font_size':10, 'align':'center', 'bold':True, 'font_color':'blue'})
        else:
            col_fmt = book.add_format({'font_name':'Arial', 'font_size':10, 'align':'center', 'bg_color':bg_colors[i]})
        sheet.set_column(r, widths[i], col_fmt)
    sheet.conditional_format(cond_range, tdtP)
    sheet.conditional_format(cond_range, tdtN)

    try:
        writer.save()
    except IOError:
        print "\nOh no! Unable to save spreadsheet :(\nMake sure you don't already have a file with the same name opened."



def select_report_date_attempts(df, report_dt):
    """Return recordings from the report_date.
    
    Parameters
    ----------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempts.
    last_bday : datetime.date
        
    Returns
    -------
    df : pandas dataframe
        A dataframe of PatchSeq recording attempts from the report date.
    """
    
    df["Date"] = df["Date"].apply(lambda x: datetime.strptime(x, "%y%m%d").date())
    df = df[df["Date"] == report_dt]
    return df


"""---------------CONSTANTS---------------"""
SPREADNAME = "formatted-patchseq-metadata.xlsx"
VALID_VALS = ["y", "n"]
p_users = {"kristenh":"P1",
           "rustym":"P2",
           "jonathant":"P3",
           "alexh":"P4",
           "brianl":"P5",
           "aarono":"P6",
           "briank":"P7",
           "lindsayn":"P8",
           "lisak":"P9",
           "ramr":"PA",
           "dijonh":"PB",
           "Kristen Hadley":"P1",
           "Rusty Mann":"P2",
           "Jonathan Ting":"P3",
           "Alex Hoggarth":"P4",
           "Brian Lee":"P5",
           "Aaron Oldre":"P6",
           "Brian Kalmbach":"P7",
           "Lindsay Ng":"P8",
           "Lisa Kim":"P9",
           "Ram Rajanbabu":"PA",
           "DiJon Hill":"PB"}

hexes = ['#F2DCDB', '#E4DFEC', '#D9EAD3', '#F4CCCC', '#CFE2F3', '#FFF2CC']
loc_dict = {"LGn core": "LGN core", "lgn core":"LGN core", "core":"LGN core", "lgn shell":"LGN shell", "shell":"LGN shell"}

"""---------------ASK USER FOR INPUT---------------"""
#STR_PROMPT = "\nWould you like to select a directory containing Patch-Seq metadata? (y / n): "
#EXPT = validated_input(STR_PROMPT, VALID_VALS)
DIRNAME = '\\\\allen\\programs\\celltypes\\workgroups\\279\\Patch-Seq\\all-metadata-files'

bday_us = CustomBusinessDay(calendar=USFederalHolidayCalendar())
last_bday = (datetime.today() - bday_us).date()
last_bday_str = last_bday.strftime("%y%m%d")

str_prompt1 = "\nWould you like to report on samples from %s? (y / n): "  %last_bday_str
valid_vals = ["y", "n"]
str_prompt2 = "Please enter date to report on (YYMMDD): "

response1 = "\nPlease try again..."
response2 = "\nPlease try again... date should be YYMMDD"

last_bday_state = validated_input(str_prompt1, response1, valid_vals)
if last_bday_state == "n":
    report_date = validated_date_input(str_prompt2, response2, valid_options=None)
    report_dt = datetime.strptime(report_date, "%y%m%d") .date()
    comparison_date = report_dt + timedelta(days=1)
else:
    report_date = last_bday_str
    report_dt = last_bday
    comparison_date = datetime.now()
    
print("Generating report for %s..." %report_date)
dated_output_name = "%s_%s.csv" %(report_date, SPREADNAME[0:-5])
dated_output_xlsx = "%s_%s.xlsx" %(report_date, SPREADNAME[0:-5])

"""---------------GET INFO FROM JSON FOLDER---------------"""
delta_mod_date = (datetime.today().date() - report_dt).days + 3
json_files, json_paths = get_jsons(dirname=DIRNAME, expt="PS", delta_days=delta_mod_date)

if len(json_paths) > 0:
    p_df = extract_PS_info(json_paths, p_users, loc_dict)
    p_df.insert(loc=26, column='Volume (ul)', value=1)
    p_df_1 = select_report_date_attempts(p_df, report_dt)
    make_PS_xlsx(DIRNAME, dated_output_xlsx, p_df_1, hexes)    
else:   
    print "There were no .json files found in %s" %DIRNAME