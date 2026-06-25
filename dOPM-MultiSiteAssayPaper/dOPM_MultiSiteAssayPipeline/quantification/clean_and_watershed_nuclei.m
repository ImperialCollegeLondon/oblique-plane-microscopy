function sgm_nuc = clean_and_watershed_nuclei(u,r,min_sieve_out_size,dmap_smooth_length,CLEARBORDER)
            z = u;
            se_r = strel('sphere',round(r));
            % remove too thin objects            
            z = imerode(z,se_r);
            z = imdilate(z,se_r);
            %            
            sgm_nuc = bwareaopen(z,min_sieve_out_size); %!!!
            %
            sgm_nuc_L = bwlabeln(sgm_nuc);
            acc = zeros(size(sgm_nuc_L));
            parfor k=1:max(sgm_nuc_L(:))  
                z = smooth_watershed((sgm_nuc_L==k),dmap_smooth_length) > 0;                                    
                z = imerode(z,se_r);
                z = imdilate(z,se_r);  
                %z = bwareaopen(z,min_sieve_out_size);
                acc = acc + (z==1);
                k
            end
            %
            acc = bwareaopen(acc,min_sieve_out_size); %!!!  
            %
            if CLEARBORDER
                acc = imclearborder(acc,26);            
            end            
            %            
            sgm_nuc = bwlabeln(acc);  
end