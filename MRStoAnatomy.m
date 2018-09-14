function [mask_fname] = MRStoAnatomy(nrrd_template, t1w_fname, MRS_fname, mask_fname)
    

    % Read the LPS template for the MRS file.
    hdr = readNrrdHeader(nrrd_template);
    
    % Read the MRS info
    [VOIPosition, FOV, mat] = getCoordinatefromRDA(MRS_fname); %Assuming MRS is in the same space as T1.
    % The mask is a box of ones
    dat = ones(FOV);
    
    mat = sortMat(mat); 
        

    % Change the header 
    hdr.sizes = FOV';
    tmp = mat';
    hdr.spacedirections = tmp(:);  % This wil rotate the box if needed
    

    % Calculate the new origin
    a = [[mat VOIPosition'];[0 0 0 1]] ;  
    b = [[eye(3) [-FOV/2]']; [0 0 0 1]];
    origin = a*b*[0 0 0 1]';
   
    hdr.spaceorigin = origin(1:3);
    
    % Write the new mask
    hdr2Nhdr(hdr,dat, [mask_fname '_jm']);
    
    % Read the T1 dimensions
    t1hdr = readNrrdHeader(t1w_fname);
    
    % Save a blank file the size of the T1.
    dat_t1 = zeros(t1hdr.sizes');
    hdr2Nhdr(t1hdr,dat_t1,[mask_fname '_zr']);
    
    
  
    % The code assumes that the RDA coordinate VOIPosition are in LPS and
    % that the coordinate is of the center of the box.
    % 
    % The direction vectors are read from the RDA, to build a box we need a
    % matrix that looks similar to:
    % -1 0 0
    % 0 1 0
    % 0 0 -1
    %
    %  The code sorts the directions to match this format.
    % We calculate the origin to be the edge of the box before it has been
    % rotated.
    %
    % The rotation is enforced by the direction matrix being written to the
    % nrrd.
    %
    % The mask is save as a nrrd, also an image of zeros the size of the T1
    % is save. Then the two are added up, so the make ends up being in the
    % same reference frame and image size as the T1.


end



