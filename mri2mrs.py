#!/usr/bin/env python

from plumbum import cli, FG
from plumbum.cmd import rm, bet, fslmaths, fast, fslswapdim, fslstats, \
    ConvertBetweenFileFormats, matlab, ImageMath, Slicer, antsApplyTransforms
import os


def run_command(command, arguments):

    command_line= f'{command}.run({arguments}, retcode=None)'

    # log the command
    log(command_line)

    # execute the command
    retcode, stdout, stderr= eval(command_line)

    if retcode==0:
        log(stdout)

    else:
        log(f'{command_line} failed.')
        log(stderr)
        exit(1)


def log(msg):
    print(msg)
    f.write(msg+'\n')

def warpDim(mri):

    try:
        fslswapdim[mri, 'LR', 'PA', 'IS', mri] & FG

    except:
    
        fslswapdim[mri, 'RL', 'PA', 'IS', mri] & FG





def createMRSmask(segment, MRSregion, MRSmask):
    fslmaths[segment, '-mul', MRSregion, MRSmask] & FG



def calcVol(region):
    vols= fslstats(region, '-V')
    return float(vols.strip(' ').split(' ')[1])

class MRS(cli.Application):
    """Calculates brain and white matter volumes given an MRS (Magnetic Resonance Spectroscopy)
     label map and a T1 image registered in the space MRS.
     Dependencies on bet, fslmaths, fast, fslswapdim, fslstats, ConvertBetweenFileFormats, matlab, Slice.
     Uses Ofer's MATLAB code (SIEMENS machine) for creating MRS region mask.
    """

    img = cli.SwitchAttr(
        ['-i', '--input'],
        cli.ExistingFile,
        help='A T1 image registered in the space of magnetic resonance spectroscopy (nrrd or nifti)',
        mandatory=True)

    case= cli.SwitchAttr(
        ['-c', '--caseID'],
        help='A T1 image registered in the space of magnetic resonance spectroscopy (nrrd or nifti)',
        mandatory=True)

    mask = cli.Flag(
        ['-m', '--mask'],
        help='''turn on this flag to mask the T1 image before running the pipeline.
                When turned on, a mask is created and the T1 image is multiplied by the mask
                before running further steps''',
        mandatory= False,
        default= False)

    region = cli.SwitchAttr(
        ['-r', '--region'],
        help='Region name (acg, agm, ltemp, pcg, pwm etc.)',
        mandatory=True)

    labelMap= cli.SwitchAttr(
        ['-l', '--labelMap'],
        cli.ExistingFile,
        help='An rda file from the scanner defining label map of a region (acg, agm, ltemp, pcg, pwm etc.)',
        mandatory=True)

    outDir = cli.SwitchAttr(
        ['-o', '--out'],
        help='''output directory where files created during the pipeline are saved
             (if already exist, it will be deleted and recreated)''',
        mandatory=True)

    betThreshold= cli.SwitchAttr(
        ['-b', '--betThreshold'],
        help='Threshold for bet mask creation',
        mandatory=False,
        default='0.3')

    def main(self):

        if not (self.img.endswith('.nrrd') or self.img.endswith('.nrrd') or
                self.img.endswith('.nii') or self.img.endswith('.nii.gz')):
            print("Invalid T1 image format, exiting ...")

        if not self.labelMap.endswith('.rda'):
            print("Invalid label map format, exiting ...")

        # if output directory exists, delete and re-create
        if os.path.exists(self.outDir):
            rm.run(['-r', self.outDir])

        os.makedirs(self.outDir)


        scriptDir= os.getcwd()
        os.chdir(self.outDir)

        global f, logFile
        logFile= 'log-{}.txt'.format(self.case)
        f= open(logFile, 'w')

        # fsl requires nifti
        if self.img.endswith('.nrrd') or self.img.endswith('.nhdr'):
            convertedImg= self.case+'-t1w.nii.gz'
            ((ConvertBetweenFileFormats[self.img, convertedImg] ) >> logFile)()

        else:
            convertedImg= self.img



        if self.mask:
            log('Creating mask and multiplying the input image by mask ...')
            bet_mask= self.case+'_mask.nii.gz' # bet names the mask like this
            bet[convertedImg, self.case, '-m', '-n', '-f', self.betThreshold] & FG

            processedImg = self.case + '-t1w-bet.nii.gz'
            fslmaths[convertedImg, '-mul', bet_mask, processedImg] & FG

        else:
            processedImg= convertedImg

        warpDim(processedImg)

        log('Segmenting T1 image to white/gray/CSF ...')
        ((fast['-o', 'fast_out', processedImg] ) >> logFile)()


        log('Creating white, gray, csf separate images ...')

        white = 'fast_out_seg.nii.gz'
        gray = 'fast_out_seg2.nii.gz'
        csf = 'fast_out_seg3.nii.gz'


        fslmaths[white, '-uthr', '1', gray] & FG
        fslmaths[gray, '-add', '1', gray] & FG
        fslmaths[gray, '-uthr', '1', gray] & FG

        fslmaths[white, '-thr', '3', csf] & FG
        fslmaths[csf, '-div', '3', csf] & FG


        # Ofer's MATLAB code reads only .nhdr file
        compatibleImg= self.case+'-t1w.nhdr'
        # TODO: Check with Ofer if he wants unprocessed image as the first argument
        ((ConvertBetweenFileFormats[processedImg, compatibleImg] ) >> logFile)()


        regionPrefix = self.region
        log('Defining MRS on T1 image using MATLAB ...')
        command= 'matlab'
        arguments= ['-singleCompThread', '-nojvm', '-nosplash', '-r',
                   "diary(\'{}\'); addpath {}; MRStoAnatomy(\'{}\', \'{}\', \'{}\', \'{}_mask\'); exit"
                   .format(logFile, scriptDir, 'tmp-sb.nhdr', compatibleImg, self.labelMap, regionPrefix)]

        # Check with Ofer:
        # Warning: File is not RAS, make sure subsequent matlab processing is consistent!
        # Warning: File is not RAS, make sure subsequent matlab processing is consistent!

        run_command(command, arguments)

        '''
        # Ofer's original command
        command= 'Slicer'
        arguments= ['--launch', 'AddScalarVolumes',
                   self.region+'_mask_zr.nhdr',
                   self.region + '_mask_jm.nhdr',
                   '--order', '0',
                   self.region + '_mask.nhdr']

        run_command(command, arguments)
        log("Converting MRS mask to nii ...")
        oldMRSmask= regionPrefix+'_mask.nhdr'
        newMRSmask= regionPrefix+'_mask.nii.gz'
        ((ConvertBetweenFileFormats[oldMRSmask, newMRSmask] ) >> logFile)()
        '''

        
        # Isaiah proposed command to replace Slicer
        resampled= self.region+'_mask_aapt.nhdr'
        antsApplyTransforms['-i', self.region + '_mask_jm.nhdr', '-r',
                            self.region+'_mask_zr.nhdr', '-o', resampled] & FG
        newMRSmask = regionPrefix + '_mask.nii.gz'
        ImageMath['3', newMRSmask, '+', self.region + '_mask_zr.nhdr', resampled] & FG
        

        warpDim(newMRSmask)

        log('Creating MRS masks ...')
        MRSmaskBrain= regionPrefix+'_MRS_mask_brain.nii.gz'
        MRSmaskWM = regionPrefix + '_MRS_mask_wm.nii.gz'
        createMRSmask(gray, newMRSmask, MRSmaskBrain)
        createMRSmask(csf, newMRSmask, MRSmaskWM)


        brainVol= calcVol(MRSmaskBrain)

        # print ROI volume
        totVol= calcVol(newMRSmask)
        log('ROI volume:{}'.format(totVol))

        # print CSF volume
        csfVol= totVol - brainVol
        log('CSF volume:{}'.format(csfVol))

        # print WM volume
        wmVol= calcVol(MRSmaskWM)
        log('WM volume:{}'.format(wmVol))
        
        
        # print GM volume
        gmVol= brainVol - wmVol
        log('GM volume:{}'.format(gmVol))

        print('Program finished, see {} for details'.format(logFile))

        os.chdir(scriptDir)
        f.close()

if __name__ == '__main__':
    MRS.run()

