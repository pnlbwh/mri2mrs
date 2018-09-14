function [mat] = sortMat(mat)


	[~,ind] = max(abs(mat));

	mat = mat(ind,:);

	% First row has to be negative
	if mat(1,1) > 0 
	    mat(1,:) = -mat(1,:);
	end

	% Second row has to be positive
	if mat(2,2) < 0 
	    mat(2,:) = -mat(2,:);
	end

	% Third row has to be negative
	if mat(3,3) > 0 
	    mat(3,:) = -mat(3,:);
	end

end
