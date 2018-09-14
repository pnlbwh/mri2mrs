function [VOIPosition, FOV, mat] = getCoordinatefromRDA(rda_filename)
    
    % Read spectroscopy data from Siemens machine
    %
    % Read a .rda file
    

    VOIPosition = zeros(1,3);
    FOV = zeros(1,3);
    mat = zeros(3,3);
    fid = fopen(rda_filename);

    head_start_text = '>>> Begin of header <<<';
    head_end_text   = '>>> End of header <<<';

    tline = fgets(fid);

    while (isempty(strfind(tline , head_end_text)))
        
        tline = fgets(fid);
        
        if ( isempty(strfind (tline , head_start_text)) + isempty(strfind (tline , head_end_text )) == 2)
            
            
            % Store this data in the appropriate format
            
            occurence_of_colon = findstr(':',tline);
            variable = tline(1:occurence_of_colon-1) ;
            value    = tline(occurence_of_colon+1 : length(tline)) ;
            
            switch variable
                case{'VOIPositionSag'}
                    VOIPosition(1) = str2num(value);
                case{'VOIPositionCor'}
                    VOIPosition(2) = str2num(value);
                case{'VOIPositionTra'}
                    VOIPosition(3) = str2num(value);
                case{'VOIThickness'}
                    FOV(3) = str2num(value);
                case{'VOIPhaseFOV'}
                    FOV(2) = str2num(value);
                case{'VOIReadoutFOV'}
                    FOV(1) = str2num(value);
                case{'RowVector[0]'}
                    mat(1,1)= str2num(value);
                case{'RowVector[1]'}
                    mat(1,2) = str2num(value);
                case{'RowVector[2]'}
                    mat(1,3) = str2num(value);
                case{'ColumnVector[0]'}
                    mat(2,1) = str2num(value);
                case{'ColumnVector[1]'}
                    mat(2,2) = str2num(value);
                case{'ColumnVector[2]'}
                    mat(2,3) = str2num(value);    
                    
            end
                       
            mat(3,:) = cross(mat(1,:),mat(2,:));
            
        end
        
    end


    fclose(fid);

end
