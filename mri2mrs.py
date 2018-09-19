#!/usr/bin/env python

from plumbum import cli, FG
from plumbum.cmd import rm, bet, fslmaths, fast, fslswapdim, fslstats, ConvertBetweenFileFormats, matlab, Slicer
import os


def log(msg):
    print(msg)
    f.write(msg+'\n')


def externalOutput(retcode, stdout, stderr):

    if not retcode:
        print(stderr)
    else:
        log(stdout)

def warpDim(mri):
    fslswapdim[mri, 'LR', 'PA', 'IS', mri] & FG


def createMRSmask(segment, MRSregion, MRSmask):
    fslmaths[segment, '-mul', MRSregion, MRSmask] & FG



def calcVol(region):
    vols= fslstats(region, '-V')
    return vols.strip(' ').split(' ')[0]

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
            bet_mask= self.case+'-t1w-mask.nii.gz'
            ((bet[convertedImg, bet_mask, '-m -n -f', self.betThreshold] ) >> logFile)()

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

        try:
            regionPrefix = self.region
            log('Defining MRS on T1 image using MATLAB ...')

            retcode, stdout, stderr= matlab.run(['-singleCompThread', '-nojvm', '-nosplash', '-r',
                   "addpath {}, MRStoAnatomy(\'{}\', \'{}\', \'{}\', \'{}_mask\'), exit"
                   .format(scriptDir, 'tmp-sb.nhdr', compatibleImg, self.labelMap, regionPrefix)])
            externalOutput(retcode, stdout, stderr)


            log('Combining the mask with the zero files to create a mask having same dimensions as that of T1, '
                'launching Slicer ...')

            retcode, stdout, stderr= Slicer.run(['--launch', 'AddScalarVolumes',
                   self.region+'_mask_zr.nhdr',
                   self.region + '_mask_jm.nhdr',
                   '--order', '0',
                   self.region + '_mask.nhdr'])
            externalOutput(retcode, stdout, stderr)


        except:
            log('MRS mask creation failed for {}, exiting ...'.format(self.img))
            exit(1)

        log("Converting MRS mask to nii ...")
        oldMRSmask= regionPrefix+'_mask.nhdr'
        newMRSmask= regionPrefix+'_mask.nii.gz'
        ((ConvertBetweenFileFormats[oldMRSmask, newMRSmask] ) >> logFile)()

        warpDim(newMRSmask)

        log('Creating MRS masks ...')
        MRSmaskBrain= regionPrefix+'_MRS_mask_brain.nii.gz'
        MRSmaskWM = regionPrefix + '_MRS_mask_wm.nii.gz'
        createMRSmask(gray, newMRSmask, MRSmaskBrain)
        createMRSmask(csf, newMRSmask, MRSmaskWM)

        log('Calculating brain volume ...')
        log('Brain volume : {}'.format(calcVol(MRSmaskBrain)))

        log('Calculating white matter volume ...')
        log('White matter volume : {}'.format(calcVol(MRSmaskWM)))

        print('Program finished, see {} for details'.format(logFile))

        os.chdir(scriptDir)
        f.close()

if __name__ == '__main__':
    MRS.run()


'''

./mri2mrs.py \
-i /rfanfs/pnl-zorro/projects/VA_AcuteTBI/MRIData/RegisteredT1/BIO_0002-registeredT1.nrrd \
-r pcg -c BIO_0002 -m \
-l /rfanfs/pnl-zorro/projects/VA_AcuteTBI/MRIData/MRS_VA_AcuteTBI/BIO_0002/BIO_0002_pcg_press.rda \
-o ~/Downloads/mri2mrs/output_test

Slicer --launch AddScalarVolumes pcg_mask_zr.nhdr pcg_mask_jm.nhdr pcg_mask.nhdr --order 0

retcode, stdout, stderr= matlab.run(['-singleCompThread', '-nojvm', '-nosplash', '-r', "addpath {}, MRStoAnatomy(\'{}\', \'{}\', \'{}\', \'{}_mask\'), exit".format(scriptDir, 'tmp-sb.nhdr', compatibleImg, self.labelMap, regionPrefix)])

'''