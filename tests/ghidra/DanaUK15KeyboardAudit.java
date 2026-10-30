// @category Dana
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;
import java.util.*;
public class DanaUK15KeyboardAudit extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(new FileWriter(getScriptArgs()[0]));
  LinkedHashSet<Long> starts=new LinkedHashSet<>(Arrays.asList(0x1007de64L,0x1007ed94L,0x1007ee0eL));
  if(getScriptArgs().length>1){starts.add(Long.parseUnsignedLong(getScriptArgs()[1],16));starts.add(0x1007ceacL);starts.add(0x1008021eL);starts.add(0x10080670L);starts.add(0x1007e4beL);starts.add(0x1007e5f2L);starts.add(0x1007ee72L);starts.add(0x1007d676L);}
  for(long p=0x10000000L;getScriptArgs().length<2 && p<0x105d0000L;p+=2){
   int v=getShort(toAddr(p))&65535;
   if(v!=0xf800&&v!=0xf802&&v!=0xf440&&v!=0xf441&&v!=0xf421)continue;
   long found=0;
   for(long a=p-2;a>=Math.max(0x10000000L,p-1024);a-=2)
    if((getShort(toAddr(a))&65535)==0x4e56){found=a;break;}
   out.printf("MMIO_WORD %08X VALUE %04X NEAR_LINK %08X\n",p,v,found);
   if(found!=0&&p<0x10100000L)starts.add(found);
  }
  ghidra.program.model.mem.MemoryBlock mmio=currentProgram.getMemory().getBlock(toAddr(0xfffff000L));
  if(mmio==null)mmio=currentProgram.getMemory().createUninitializedBlock("VZ_MMIO",toAddr(0xfffff000L),0x1000,false);
  mmio.setVolatile(true);
  DecompInterface d=new DecompInterface();d.openProgram(currentProgram);
  for(long start:starts){
   out.printf("FUNCTION %08X\n",start);
   clearListing(toAddr(start),toAddr(start+0x800));disassemble(toAddr(start));
   long pc=start;
   for(int n=0;n<600;n++){
    Instruction ins=getInstructionAt(toAddr(pc));
    if(ins==null){disassemble(toAddr(pc));ins=getInstructionAt(toAddr(pc));}
    if(ins==null){out.printf("%08X UNDECODED\n",pc);break;}
    out.printf("%08X %s",pc,ins);
    boolean trap=ins.getMnemonicString().equalsIgnoreCase("trap");
    if(trap){out.printf(" PALM_TRAP=%04X",getShort(toAddr(pc+2))&65535);ins.setFallThrough(toAddr(pc+4));}
    out.println();pc+=ins.getLength()+(trap?2:0);
    if(ins.getMnemonicString().equalsIgnoreCase("rts")||ins.getMnemonicString().equalsIgnoreCase("rte"))break;
   }
   Function f=getFunctionAt(toAddr(start));if(f==null)try{f=createFunction(toAddr(start),null);}catch(Exception e){}
   if(f!=null){DecompileResults r=d.decompileFunction(f,15,monitor);if(r.decompileCompleted())out.println(r.getDecompiledFunction().getC());}
  }d.dispose();out.close();
 }
}
