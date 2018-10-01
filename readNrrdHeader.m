function headerInfo = readNrrdHeader( nhdrFileName )

% reads all the header information from a nrrd file
% assumes a nhdr, otherwise it will not work
%
% headerInfo = readNrrdHeader( nhdrFileName )
%
% marc@bwh.harvard.edu

[pathstr,matFileName,ext] = fileparts( nhdrFileName );

if (~strcmp( upper(ext), '.NHDR' ) )
  fprintf('ABORT: %s does not seem to be an nhdr.\n', nhdrFileName );
  return;
end

clear headerInfo;

fidr = fopen( nhdrFileName, 'r' );


while ( ~feof(fidr) )

  cs = fgetl( fidr );
  csU = upper( cs );
  
  if isempty(cs)
      continue;
  end
  
  if ( foundKeyword( 'CONTENT:', cs ) )
    
    headerInfo.content = removeExcessDelimiters( cs( length('CONTENT:')+1:end ), ' ');
    
  elseif ( foundKeyword('TYPE:', cs ) )
    
    headerInfo.type = removeExcessDelimiters( cs( length('TYPE:')+1:end ), ' ');
    
  elseif ( foundKeyword('ENDIAN:', cs ) )
    
    headerInfo.endian = removeExcessDelimiters( cs( length('ENDIAN:')+1:end ), ' ');
    
  elseif ( foundKeyword('ENCODING:', cs ) )
    
    headerInfo.encoding = removeExcessDelimiters( cs( length('ENCODING:')+1:end ), ' ');
    
  elseif ( foundKeyword('DATA FILE:', cs ) )
    
    headerInfo.datafile = removeExcessDelimiters( cs( length('DATA FILE:')+1:end ), ' ');
  
  elseif ( foundKeyword('DIMENSION:', cs ) )
    
    headerInfo.dimension = sscanf( cs( length('DIMENSION:')+1:end ), '%i' );
    
  elseif ( foundKeyword('SPACE:', cs ) )
    
    headerInfo.space = removeExcessDelimiters( cs( length('SPACE:')+1:end ), ' ');
    iLocation = strfind( csU(length('SPACE:')+1:end ), 'RIGHT-ANTERIOR-SUPERIOR'); % only implemented for RAS
    if ( iLocation>0 )
      iIsRas = 1;
    else
      fprintf('Warning: File is not RAS, make sure subsequent matlab processing is consistent!\n');
    end
    
  elseif ( foundKeyword('SPACE DIRECTIONS:', cs ) )
    %% Added 'none' for 4D arrays - ofer pasternak 6/3/11
    iSD = extractNumbersWithout( cs(length('SPACE DIRECTIONS:')+1:end), {'(',')',',','none'} );

    if (length(iSD)~=9)
      fprintf('Warning: %i space directions found.\n', iSD );
    end
    
    headerInfo.spacedirections = iSD;
    
  elseif ( foundKeyword('SIZES:', cs ) )
    
    iSizes = sscanf( cs(length('SIZES:')+1:end), '%i' ); % parse sizes
    headerInfo.sizes = iSizes;
    
  elseif ( foundKeyword('THICKNESSES:', cs ) )

    sThicknesses = extractStringList( cs(length('THICKNESSES:')+1:end) );
    iThicknesses = [];
    lenThicknesses = length( sThicknesses );
    for iI=1:lenThicknesses
      iThicknesses = [iThicknesses, str2num( sThicknesses{iI} ) ];
    end
    headerInfo.thicknesses = iThicknesses;
    
  elseif ( foundKeyword('KINDS:', cs ) )
    
    headerInfo.kinds = extractStringList( cs(length('KINDS:')+1:end) );
    
  elseif ( foundKeyword('CENTERINGS:', cs ) )
    
    headerInfo.centerings = extractStringList( cs(length('CENTERINGS:')+1:end ) );
    
  elseif ( foundKeyword('SPACE UNITS:', cs ) )
    
    headerInfo.spaceunits = extractStringList( cs(length('SPACE UNITS:')+1:end ) );
    
  elseif ( foundKeyword('SPACE ORIGIN:', cs ) )

    iSO = extractNumbersWithout( cs(length('SPACE ORIGIN:')+1:end), {'(',')',','} );
    
    if (length(iSO)~=3)
      fprintf('Warning: %i space directions found.\n', iSD );
    end
    
    headerInfo.spaceorigin = iSO;
    
    
  elseif ( foundKeyword('MEASUREMENT FRAME:', cs ) )
    
    iMF = extractNumbersWithout( cs(length('MEASUREMENT FRAME:')+1:end), {'(',')',','} );
    headerInfo.measurementframe = iMF;
    
  elseif ( foundKeyword('MODALITY', cs ) )
    
    headerInfo.modality = removeExcessDelimiters( extractKeyValueString( cs(length('MODALITY')+1:end ) ), ' ');
    
  elseif ( foundKeyword('DWMRI_B-VALUE', cs ) )
    
    headerInfo.bvalue = str2num( extractKeyValueString( cs(length('DWMRI_B-VALUE')+1:end ) ) );
    
  elseif ( foundKeyword('DWMRI_GRADIENT_', cs ) )
    
    [iGNr, dwiGradient] = extractGradient( cs(length('DWMRI_GRADIENT_')+1:end ) );
    headerInfo.gradients(iGNr+1,:) = dwiGradient;
    
  else
    
    % let's see if we are dealing with a comment
    
    csTmp = removeExcessDelimiters( cs, ' ' );
    if ( csTmp(1)~='#' & ~strcmp(cs(1:4),'NRRD') )
      fprintf('Warning: Could not parse input line: %s \n', cs );
    end
    
  end
  
end


fclose( fidr );


return


function [iGNr, dwiGradient] = extractGradient( st )

% first get the gradient number

iGNr = str2num( st(1:4) );

% find where the assignment is

assgnLoc = strfind( st, ':=' );

if ( isempty(assgnLoc) )
  dwiGradient = [];
  return;
else
  
  dwiGradient = sscanf( st(assgnLoc+2:end), '%f' );
  
end

return


function kvs = extractKeyValueString( st )

assgnLoc = strfind( st, ':=' );

if ( isempty(assgnLoc) )
  kvs = [];
  return;
else
  
  kvs = st(assgnLoc(1)+2:end);
  
end

return

function sl = extractStringList( strList )

strList = removeExcessDelimiters( strList, ' ' );

delimiterIndices = strfind(strList,' ');

numDelimiters = length(delimiterIndices);

if (numDelimiters>=1)
  sl{1} = strList(1:delimiterIndices(1)-1);
else
  sl{1} = strList;
end

for iI=1:numDelimiters-1
  sl{iI+1} = strList(delimiterIndices(iI)+1:delimiterIndices(iI+1)-1);
end

if (numDelimiters>=2)
  sl{numDelimiters+1} = strList(delimiterIndices(end)+1:end);
end

return

function sl = removeExcessDelimiters( strList, delim )

if ( isempty( strList ) )
    return;
end

indxList = [];
len = length( strList );

iStart = 1;

while ( iStart<len & strList(iStart)==delim )
  iStart = iStart+1;
end

iEnd = len;

while ( iEnd>1 & strList(iEnd)==delim )
  iEnd = iEnd-1;
end

iLastWasDelimiter = 0;

for iI=iStart:iEnd
  
  if ( strList(iStart)~=delim )
    indxList = [indxList; iI ];
    iLastWasDelimiter = 0;
  else
    if ( ~iLastWasDelimiter )
      indxList = [indxList; iI];
    end
    iLastWasDelimiter = 1;
  end
  
end

sl = strList(indxList);

return


function iNrs = extractNumbersWithout( inputString, withoutTokens )

auxStr = inputString;

for iI=1:length( withoutTokens )
  
  auxStr = strrep( auxStr, withoutTokens{iI}, ' ' );
  
end

iNrs = sscanf( auxStr, '%f' );

return

function fk = foundKeyword( keyWord, cs )

csU = upper( cs );
len = length( csU );
lenKeyword = length( keyWord );

keyWordU = upper( keyWord );

fk = 0;

if ( len<lenKeyword )
  fk = 0;
  return
end

if ( strcmp( csU(1:lenKeyword),keyWordU ) )
  fk = 1;
  return
else
  fk = 0;
  return
end

return
